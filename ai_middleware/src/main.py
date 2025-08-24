from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
import os
import asyncio
import json
from dotenv import load_dotenv

from .odoo_client import OdooClient
from .ai_agent import AIAgent

load_dotenv()

app = FastAPI(title="AI Middleware for Odoo Live Chat")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
odoo_client = OdooClient(
    url=os.getenv('ODOO_URL'),
    db=os.getenv('ODOO_DB'),
    username=os.getenv('ODOO_USERNAME'),
    password=os.getenv('ODOO_PASSWORD')
)

ai_agent = AIAgent(
    api_key=os.getenv('OPENAI_API_KEY'),
    confidence_threshold=float(os.getenv('CONFIDENCE_THRESHOLD', 0.7))
)

# Load knowledge base on startup
knowledge_dir = os.path.join(os.path.dirname(__file__), '..', 'knowledge')
if os.path.exists(knowledge_dir):
    ai_agent.load_knowledge_base(knowledge_dir)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
        self.session_tasks: Dict[int, asyncio.Task] = {}
    
    async def connect(self, websocket: WebSocket, session_id: int):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        # Start monitoring task for this session
        task = asyncio.create_task(self.monitor_session(session_id))
        self.session_tasks[session_id] = task
    
    def disconnect(self, session_id: int):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.session_tasks:
            self.session_tasks[session_id].cancel()
            del self.session_tasks[session_id]
    
    async def send_message(self, session_id: int, message: dict):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(json.dumps(message))
            except:
                self.disconnect(session_id)
    
    async def monitor_session(self, session_id: int):
        last_message_id = 0
        while session_id in self.active_connections:
            try:
                # Check session status
                is_active = odoo_client.is_session_active(session_id)
                if not is_active:
                    await self.send_message(session_id, {
                        "type": "session_ended",
                        "message": "Agent has left the chat"
                    })
                    break
                
                # Get new messages
                messages = odoo_client.get_session_messages(session_id)
                if messages:
                    new_messages = [msg for msg in messages if msg['id'] > last_message_id]
                    if new_messages:
                        for msg in new_messages:
                            if msg['body'] == 'SESSION_ENDED':
                                await self.send_message(session_id, {
                                    "type": "session_ended",
                                    "message": "Agent has left the chat"
                                })
                                return
                            else:
                                await self.send_message(session_id, {
                                    "type": "message",
                                    "data": msg
                                })
                            last_message_id = max(last_message_id, msg['id'])
                
                await asyncio.sleep(2)  # Check every 2 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Monitor error for session {session_id}: {e}")
                await asyncio.sleep(5)

manager = ConnectionManager()

class ChatMessage(BaseModel):
    message: str
    visitor_name: Optional[str] = "Anonymous"
    session_id: Optional[str] = None
    context: Optional[str] = ""

class ChatResponse(BaseModel):
    response: str
    handoff_needed: bool
    confidence: float
    odoo_session_id: Optional[int] = None

@app.post("/chat", response_model=ChatResponse)
async def handle_chat(chat_message: ChatMessage):
    """Main endpoint for handling chat messages"""
    try:
        # If session_id exists, send message directly to Odoo
        if chat_message.session_id:
            success = odoo_client.send_message_to_session(
                int(chat_message.session_id), 
                chat_message.message, 
                chat_message.visitor_name
            )
            
            if success:
                return ChatResponse(
                    response="",
                    handoff_needed=False,
                    confidence=1.0,
                    odoo_session_id=int(chat_message.session_id)
                )
            else:
                return ChatResponse(
                    response="SESSION_ENDED",
                    handoff_needed=False,
                    confidence=0.0
                )
        
        # Process message with AI agent
        handoff_needed, ai_response, confidence = ai_agent.should_handoff(
            chat_message.message, 
            chat_message.context
        )
        
        odoo_session_id = None
        
        if handoff_needed:
            # Create Odoo live chat session
            odoo_session_id = odoo_client.create_live_chat_session(
                visitor_name=chat_message.visitor_name,
                message=chat_message.message
            )
            
            if odoo_session_id:
                ai_response = f"I've connected you with a human agent (Session #{odoo_session_id}). The agent will see your request: '{chat_message.message}'. Please wait for their response."
            else:
                ai_response = "I'm having trouble connecting you to an agent. Please try again."
        
        return ChatResponse(
            response=ai_response,
            handoff_needed=handoff_needed,
            confidence=confidence,
            odoo_session_id=odoo_session_id
        )
        
    except Exception as e:
        print(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

@app.get("/messages/{session_id}")
async def get_messages(session_id: int):
    """Get new messages from Odoo live chat session"""
    try:
        messages = odoo_client.get_session_messages(session_id)
        return {"messages": messages}
    except Exception as e:
        print(f"Error getting messages: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting messages: {str(e)}")

@app.get("/session/{session_id}/status")
async def get_session_status(session_id: int):
    """Check if session is still active"""
    try:
        is_active = odoo_client.is_session_active(session_id)
        return {"active": is_active}
    except Exception as e:
        print(f"Error checking session status: {e}")
        return {"active": False}

class FeedbackRequest(BaseModel):
    session_id: int
    rating: str
    comment: Optional[str] = ""

@app.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """Submit feedback for a chat session"""
    try:
        # Store feedback in Odoo
        success = odoo_client.store_feedback(
            feedback.session_id,
            feedback.rating,
            feedback.comment
        )
        
        if success:
            return {"status": "success", "message": "Feedback submitted"}
        else:
            return {"status": "error", "message": "Failed to submit feedback"}
            
    except Exception as e:
        print(f"Feedback error: {e}")
        raise HTTPException(status_code=500, detail=f"Error submitting feedback: {str(e)}")

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: int):
    """WebSocket endpoint for real-time chat updates"""
    try:
        await manager.connect(websocket, session_id)
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client (like ping/pong)
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get('type') == 'ping':
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"WebSocket message error: {e}")
                break
                
    except Exception as e:
        print(f"WebSocket connection error: {e}")
    finally:
        manager.disconnect(session_id)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "AI Middleware"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)