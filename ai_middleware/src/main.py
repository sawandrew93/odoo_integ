from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os
import json
from dotenv import load_dotenv

from .odoo_client import OdooClient
from .ai_agent import AIAgent
from .websocket_manager import WebSocketManager

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
    api_key=os.getenv('GEMINI_API_KEY'),
    confidence_threshold=float(os.getenv('CONFIDENCE_THRESHOLD', 0.7))
)

# Load knowledge base on startup
knowledge_dir = os.path.join(os.path.dirname(__file__), '..', 'knowledge')
if os.path.exists(knowledge_dir):
    ai_agent.load_knowledge_base(knowledge_dir)

# Initialize WebSocket manager
ws_manager = WebSocketManager(odoo_client)

class ChatMessage(BaseModel):
    message: str
    visitor_name: Optional[str] = "Anonymous"
    session_id: Optional[str] = None
    context: Optional[str] = ""
    
    class Config:
        extra = "ignore"  # Ignore extra fields

class ChatResponse(BaseModel):
    response: str
    handoff_needed: bool
    confidence: float
    odoo_session_id: Optional[int] = None

@app.post("/chat", response_model=ChatResponse)
async def handle_chat(chat_message: ChatMessage):
    """Main endpoint for handling chat messages"""
    try:
        print(f"Received chat message: {chat_message}")
        
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
                ai_response = f"I've connected you with a human agent (Session #{odoo_session_id}). Please wait for their response."
            else:
                ai_response = "Our support team is currently offline. Please check back soon!"
        
        return ChatResponse(
            response=ai_response,
            handoff_needed=handoff_needed,
            confidence=confidence,
            odoo_session_id=odoo_session_id
        )
        
    except Exception as e:
        print(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

@app.get("/session/{session_id}/status")
async def get_session_status(session_id: int):
    """Check if session is still active (minimal check only)"""
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
        await ws_manager.connect(websocket, session_id)
        
        # Keep connection alive and handle ping/pong
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get('type') == 'ping':
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"WebSocket error: {e}")
                break
                
    except Exception as e:
        print(f"WebSocket connection failed: {e}")
    finally:
        ws_manager.disconnect(session_id)

@app.get("/widget.js")
async def get_widget():
    """Serve the embeddable widget"""
    widget_path = os.path.join(os.path.dirname(__file__), '..', 'widget.js')
    return FileResponse(widget_path, media_type='application/javascript')

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "AI Middleware"}

@app.get("/connections")
async def get_connections():
    """Get active WebSocket connections"""
    return {
        "websocket_connections": len(ws_manager.connections),
        "active_sessions": list(ws_manager.connections.keys()),
        "monitoring_tasks": len(ws_manager.tasks)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)