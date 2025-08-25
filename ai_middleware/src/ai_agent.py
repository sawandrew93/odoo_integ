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
        if session_id and session_id in self.pending_handoff:
            if any(word in message_lower for word in ['yes', 'okay', 'ok', 'sure', 'please']):
                del self.pending_handoff[session_id]
                return True, "I'll connect you with a human agent.", 0.0
            elif any(word in message_lower for word in ['no', 'not now', 'later']):
                del self.pending_handoff[session_id]
                return False, "No problem! How else can I help you?", 0.9
        
        # Check for explicit human agent requests
        human_keywords = ['talk to support', 'speak to support', 'human agent', 'live agent', 'representative', 'talk to someone', 'speak to person', 'connect me to agent']
        if any(keyword in message_lower for keyword in human_keywords) or ('support' in message_lower and ('talk' in message_lower or 'speak' in message_lower)):
            return True, "I'll connect you with a human agent.", 0.0
        
        # Handle greetings
        greeting_words = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening', 'how are you']
        if any(word in message_lower for word in greeting_words):
            return False, "Hello! How can I help you today?", 0.9
        
        # Search knowledge base
        relevant_docs = self.kb.search(message, top_k=3)
        
        # Use knowledge base for known questions with higher threshold
        if relevant_docs and relevant_docs[0][1] > 0.6:
            kb_content = relevant_docs[0][0]
            if 'A:' in kb_content:
                answer = kb_content.split('A:')[1].split('Q:')[0].strip()
                return False, answer, relevant_docs[0][1]
        
        # For unknown questions, offer handoff
        if session_id:
            self.pending_handoff[session_id] = True
        return False, "I don't have information about that. I can connect you with our support representative if you want.", 0.3