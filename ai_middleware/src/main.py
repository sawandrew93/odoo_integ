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
import re

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

# Initialize AI agent with error handling
try:
    ai_agent = AIAgent(
        api_key=os.getenv('GEMINI_API_KEY'),
        confidence_threshold=float(os.getenv('CONFIDENCE_THRESHOLD', 0.7)),
        supabase_url=os.getenv('SUPABASE_URL'),
        supabase_key=os.getenv('SUPABASE_KEY')
    )
except Exception as e:
    print(f"Warning: AI Agent initialization failed: {e}")
    ai_agent = None

# Load knowledge base on startup
knowledge_dir = os.path.join(os.path.dirname(__file__), '..', 'knowledge')
if ai_agent and os.path.exists(knowledge_dir):
    try:
        ai_agent.load_knowledge_base(knowledge_dir)
    except Exception as e:
        print(f"Warning: Failed to load knowledge base: {e}")

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

def create_chunks(text, filename="", chunk_size=1000, overlap=200):
    """Create overlapping chunks from text using sentence boundaries"""
    if not text or len(text.strip()) < 50:
        return []
    
    # Split into sentences
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    chunks = []
    current_chunk = ""
    current_length = 0
    
    for sentence in sentences:
        sentence_length = len(sentence)
        
        # If adding this sentence exceeds chunk size, save current chunk
        if current_length + sentence_length > chunk_size and current_chunk:
            chunks.append({"content": current_chunk.strip(), "filename": filename})
            
            # Start new chunk with overlap
            words = current_chunk.split()
            overlap_words = words[-overlap//5:] if len(words) > overlap//5 else words
            current_chunk = ' '.join(overlap_words) + ' ' + sentence
            current_length = len(current_chunk)
        else:
            current_chunk += ' ' + sentence
            current_length = len(current_chunk)
    
    # Add final chunk
    if current_chunk.strip():
        chunks.append({"content": current_chunk.strip(), "filename": filename})
    
    # Filter out very short chunks
    chunks = [chunk for chunk in chunks if len(chunk["content"]) > 100]
    
    print(f"Created {len(chunks)} chunks from {len(text)} characters")
    return chunks

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
        if not ai_agent:
            # Fallback if AI agent not initialized
            handoff_needed = True
            ai_response = "AI service temporarily unavailable. Connecting you with support."
            confidence = 0.0
        else:
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
    if not ai_agent or not ai_agent.kb or not ai_agent.kb.supabase:
        raise HTTPException(status_code=500, detail="Knowledge base not properly configured. Please check Supabase credentials.")
    
    processed = 0
    
    for file in files:
        try:
            content = ""
            
            if file.filename.endswith('.pdf'):
                # Extract text from PDF
                pdf_content = await file.read()
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
                
                full_text = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text.strip():
                        full_text += page_text + " "
                
                # Clean the text
                content = ' '.join(full_text.split())  # Remove extra whitespace
                    
            elif file.filename.endswith('.txt'):
                # Read text file
                content = (await file.read()).decode('utf-8')
            
            if content.strip():
                # Create proper chunks using sentence-based chunking
                chunks = create_chunks(content, file.filename)
                print(f"📄 Processing {file.filename}: {len(chunks)} chunks", flush=True)
                if chunks:
                    ai_agent.kb.add_documents_with_filename(chunks)
                    processed += 1
                else:
                    print(f"⚠️ No valid chunks found in {file.filename}", flush=True)
                
        except Exception as e:
            print(f"❌ Error processing {file.filename}: {e}", flush=True)
            continue
    
    return {"processed": processed, "message": f"Successfully processed {processed} files"}

@app.get("/admin/knowledge-list")
async def list_knowledge(token: str = Depends(verify_admin_token)):
    """List all knowledge base documents grouped by filename (protected)"""
    if not ai_agent or not ai_agent.kb or not ai_agent.kb.supabase:
        print(f"Knowledge base check failed: ai_agent={ai_agent is not None}, kb={ai_agent.kb if ai_agent else None}, supabase={ai_agent.kb.supabase if ai_agent and ai_agent.kb else None}")
        raise HTTPException(status_code=500, detail="Knowledge base not properly configured. Please check Supabase credentials.")
    
    try:
        print("Fetching knowledge embeddings from Supabase...")
        result = ai_agent.kb.supabase.table('knowledge_embeddings').select('filename').execute()
        print(f"Supabase result: {result}")
        
        # Group by filename and count chunks
        files = {}
        for row in result.data:
            filename = row.get('filename', 'Unknown')
            if filename in files:
                files[filename] += 1
            else:
                files[filename] = 1
        
        # Convert to list format
        file_list = [{'filename': name, 'chunks': count} for name, count in files.items()]
        print(f"Returning file list: {file_list}")
        return sorted(file_list, key=lambda x: x['filename'])
    except Exception as e:
        print(f"Error in list_knowledge: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/knowledge/{filename}")
async def delete_knowledge_file(filename: str, token: str = Depends(verify_admin_token)):
    """Delete all chunks of a PDF file (protected)"""
    if not ai_agent or not ai_agent.kb or not ai_agent.kb.supabase:
        raise HTTPException(status_code=500, detail="Knowledge base not properly configured. Please check Supabase credentials.")
    
    try:
        result = ai_agent.kb.supabase.table('knowledge_embeddings').delete().eq('filename', filename).execute()
        deleted_count = len(result.data) if result.data else 0
        return {"message": f"Deleted {deleted_count} chunks from {filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/knowledge/{filename}/chunks")
async def get_file_chunks(filename: str, token: str = Depends(verify_admin_token)):
    """Get all chunks for a specific file (protected)"""
    if not ai_agent or not ai_agent.kb or not ai_agent.kb.supabase:
        raise HTTPException(status_code=500, detail="Knowledge base not properly configured. Please check Supabase credentials.")
    
    try:
        result = ai_agent.kb.supabase.table('knowledge_embeddings').select('id, content').eq('filename', filename).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)