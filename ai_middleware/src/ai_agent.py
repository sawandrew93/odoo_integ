import os
from typing import Dict, Tuple, Optional
import google.generativeai as genai
from .knowledge_base import KnowledgeBase

class AIAgent:
    def __init__(self, api_key: str, confidence_threshold: float = 0.7):
        self.api_key = api_key
        self.confidence_threshold = confidence_threshold
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        self.kb = KnowledgeBase(api_key)
        self.system_message = "You are a customer support AI. Only answer questions based on the provided knowledge base. If you don't have the information, say you don't have it and offer to connect with a support representative."
        self.pending_handoff = {}
        
    def load_knowledge_base(self, directory: str):
        """Load knowledge base from directory"""
        self.kb.load_from_directory(directory)
    
    def should_handoff(self, message: str, context: str = "", session_id: str = None) -> Tuple[bool, str, float]:
        """Determine if message should be handed off to human agent"""
        message_lower = message.lower().strip()
        
        # Check if user is responding to handoff offer
        session_key = session_id or 'default'
        if session_key in self.pending_handoff:
            if any(word in message_lower for word in ['yes', 'okay', 'ok', 'sure', 'please']):
                del self.pending_handoff[session_key]
                return True, "Connecting you with a human agent now...", 0.0
            elif any(word in message_lower for word in ['no', 'not now', 'later']):
                del self.pending_handoff[session_key]
                return False, "No problem! How else can I help you?", 0.9
        
        # Check for explicit human agent requests
        human_keywords = ['talk to support', 'speak to support', 'human agent', 'live agent', 'representative', 'talk to someone', 'speak to person', 'connect me', 'pls connect']
        if any(keyword in message_lower for keyword in human_keywords) or ('support' in message_lower and ('talk' in message_lower or 'speak' in message_lower)):
            return True, "I'll connect you with a human agent.", 0.0
        
        # Handle greetings
        greeting_words = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening', 'how are you']
        if any(word in message_lower for word in greeting_words):
            return False, "Hello! How can I help you today?", 0.9
        
        # Handle meta questions about the AI
        meta_questions = ['what can i ask', 'what can you answer', 'what do you know', 'what information do you have']
        if any(meta in message_lower for meta in meta_questions):
            return False, "I can help you with questions about our business hours, return policy, password reset, and order tracking. What would you like to know?", 0.9
        
        # Search knowledge base with exact keyword matching first
        if 'office hours' in message_lower or 'business hours' in message_lower:
            return False, "We are open Monday to Friday from 9 AM to 6 PM EST.", 0.9
        elif 'return policy' in message_lower or 'return' in message_lower:
            return False, "We accept returns within 30 days of purchase. Items must be in original condition.", 0.9
        elif 'password' in message_lower and 'reset' in message_lower:
            return False, "Click on 'Forgot Password' on the login page and follow the instructions sent to your email.", 0.9
        elif 'track' in message_lower and 'order' in message_lower:
            return False, "You can track your order by logging into your account and visiting the Orders section.", 0.9
        
        # For unknown questions, offer handoff
        session_key = session_id or 'default'
        self.pending_handoff[session_key] = True
        return False, "I don't have information about that. I can connect you with our support representative if you want.", 0.3