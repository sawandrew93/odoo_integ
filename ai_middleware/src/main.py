from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional, List
import os
import json
from dotenv import load_dotenv
import PyPDF2
import io
import secrets
import hashlib

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
    confidence_threshold=float(os.getenv('CONFIDENCE_THRESHOLD', 0.7)),
    supabase_url=os.getenv('SUPABASE_URL'),
    supabase_key=os.getenv('SUPABASE_KEY')
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

class LoginRequest(BaseModel):
    username: str
    password: str

# Simple token storage (in production, use Redis or database)
valid_tokens = set()

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
            chat_message.context,
            chat_message.session_id
        )
        
        odoo_session_id = None
        
        if handoff_needed:
            # Get conversation history and create Odoo live chat session
            conversation_history = ai_agent.get_conversation_history(chat_message.session_id)
            if conversation_history:
                formatted_history = "\n".join([f"• {line}" for line in conversation_history.split("\n")])
                full_message = f"📋 Previous Conversation:\n{formatted_history}\n\n🔹 Current Request: {chat_message.message}"
            else:
                full_message = chat_message.message
            
            odoo_session_id = odoo_client.create_live_chat_session(
                visitor_name=chat_message.visitor_name,
                message=full_message
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

def verify_admin_token(authorization: str = Header(None)):
    """Verify admin authentication token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    try:
        token = authorization.replace('Bearer ', '')
        if token not in valid_tokens:
            raise HTTPException(status_code=401, detail="Invalid token")
        return token
    except:
        raise HTTPException(status_code=401, detail="Invalid authorization format")

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page():
    """Admin login page"""
    template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'admin_login.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()

@app.post("/admin/login")
async def admin_login(login_data: LoginRequest):
    """Admin login endpoint"""
    admin_username = os.getenv('ADMIN_USERNAME', 'admin')
    admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
    
    # Hash the provided password for comparison
    provided_hash = hashlib.sha256(login_data.password.encode()).hexdigest()
    expected_hash = hashlib.sha256(admin_password.encode()).hexdigest()
    
    if login_data.username == admin_username and provided_hash == expected_hash:
        # Generate secure token
        token = secrets.token_urlsafe(32)
        valid_tokens.add(token)
        return {"token": token, "message": "Login successful"}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/admin")
async def admin_panel():
    """Knowledge base admin panel - handles auth via JavaScript"""
    # Always serve the admin panel, let JavaScript handle auth check
    template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'knowledge_upload.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return HTMLResponse(content=f.read())

@app.get("/admin/")
async def admin_redirect():
    """Redirect /admin/ to login"""
    return RedirectResponse(url="/admin/login")

@app.post("/admin/upload-knowledge")
async def upload_knowledge(files: List[UploadFile] = File(...), token: str = Depends(verify_admin_token)):
    """Upload and process knowledge files (protected)"""
    processed = 0
    
    for file in files:
        try:
            content = ""
            
            if file.filename.endswith('.pdf'):
                # Extract text from PDF
                pdf_content = await file.read()
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
                
                for page in pdf_reader.pages:
                    content += page.extract_text() + "\n"
                    
            elif file.filename.endswith('.txt'):
                # Read text file
                content = (await file.read()).decode('utf-8')
            
            if content.strip():
                # Split into chunks and add to knowledge base
                chunks = [chunk.strip() for chunk in content.split('\n\n') if chunk.strip()]
                ai_agent.kb.add_documents(chunks)
                processed += 1
                
        except Exception as e:
            print(f"Error processing {file.filename}: {e}")
            continue
    
    return {"processed": processed, "message": f"Successfully processed {processed} files"}

@app.get("/admin/knowledge-list")
async def list_knowledge(token: str = Depends(verify_admin_token)):
    """List all knowledge base documents (protected)"""
    if not ai_agent.kb.supabase:
        return []
    
    try:
        result = ai_agent.kb.supabase.table('knowledge_embeddings').select('id, content').execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/knowledge/{doc_id}")
async def delete_knowledge(doc_id: int, token: str = Depends(verify_admin_token)):
    """Delete a knowledge document (protected)"""
    if not ai_agent.kb.supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    
    try:
        ai_agent.kb.supabase.table('knowledge_embeddings').delete().eq('id', doc_id).execute()
        return {"message": "Document deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)