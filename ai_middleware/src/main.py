from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
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

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "AI Middleware"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)