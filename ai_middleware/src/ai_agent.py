import os
from typing import Dict, Tuple, Optional
import google.generativeai as genai
from .knowledge_base import KnowledgeBase

class AIAgent:
    def __init__(self, api_key: str, confidence_threshold: float = 0.7, supabase_url: str = None, supabase_key: str = None):
        self.api_key = api_key
        self.confidence_threshold = confidence_threshold
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        self.kb = KnowledgeBase(api_key, supabase_url, supabase_key)
        self.system_message = "You are a customer support AI. Only answer questions based on the provided knowledge base. If you don't have the information, say you don't have it and offer to connect with a support representative."
        self.pending_handoff = {}
        self.conversation_history = {}
        
    def load_knowledge_base(self, directory: str):
        """Load knowledge base from directory"""
        self.kb.load_from_directory(directory)
    
    def should_handoff(self, message: str, context: str = "", session_id: str = None) -> Tuple[bool, str, float]:
        """Determine if message should be handed off to human agent"""
        message_lower = message.lower().strip()
        session_key = session_id or 'default'
        
        # Track conversation history
        if session_key not in self.conversation_history:
            self.conversation_history[session_key] = []
        self.conversation_history[session_key].append(f"Visitor: {message}")
        
        # Check if user is responding to handoff offer
        if session_key in self.pending_handoff:
            if any(word in message_lower for word in ['yes', 'okay', 'ok', 'sure', 'please']):
                del self.pending_handoff[session_key]
                response = "Connecting you with a human agent now..."
                self.conversation_history[session_key].append(f"AI: {response}")
                return True, response, 0.0
            elif any(word in message_lower for word in ['no', 'not now', 'later']):
                del self.pending_handoff[session_key]
                response = "No problem! How else can I help you?"
                self.conversation_history[session_key].append(f"AI: {response}")
                return False, response, 0.9
        
        # Check for explicit human agent requests
        human_keywords = ['talk to support', 'speak to support', 'human agent', 'live agent', 'representative', 'talk to someone', 'speak to person', 'connect me', 'pls connect', 'talk to agent']
        if any(keyword in message_lower for keyword in human_keywords) or ('support' in message_lower and ('talk' in message_lower or 'speak' in message_lower)) or ('agent' in message_lower and ('talk' in message_lower or 'speak' in message_lower)):
            response = "I'll connect you with a human agent."
            self.conversation_history[session_key].append(f"AI: {response}")
            return True, response, 0.0
        
        # Handle common patterns first
        if any(word in message_lower for word in ['hi', 'hello', 'hey']):
            response = "Hello! How can I help you today?"
            self.conversation_history[session_key].append(f"AI: {response}")
            return False, response, 0.9
        elif 'how are you' in message_lower:
            response = "I'm doing well, thank you! How can I assist you today?"
            self.conversation_history[session_key].append(f"AI: {response}")
            return False, response, 0.9
        elif any(meta in message_lower for meta in ['what can i ask', 'what can you help', 'what do you know']):
            response = "I can help you with questions about our business hours, return policy, password reset, and order tracking. What would you like to know?"
            self.conversation_history[session_key].append(f"AI: {response}")
            return False, response, 0.9
        
        # Use AI to generate response based on knowledge base
        try:
            # Get relevant knowledge from knowledge base
            relevant_docs = self.kb.search(message, top_k=3)
            
            # Create context from knowledge base
            context = "\n".join([doc['content'] for doc in relevant_docs]) if relevant_docs else ""
            
            # Create AI prompt with better instructions
            prompt = f"""
You are a helpful customer support assistant. Answer the user's question based ONLY on the provided knowledge base.

Knowledge Base:
{context}

User Question: {message}

Instructions:
- If the knowledge base contains relevant information, provide a helpful answer
- If the knowledge base doesn't contain the information needed, respond with: "I don't have information about that. I can connect you with our support representative if you want."
- Be concise and friendly
- Don't make up information not in the knowledge base

Answer:"""
            
            # Generate response using Gemini
            ai_response = self.model.generate_content(prompt)
            response = ai_response.text.strip()
            
            # Check if AI says it doesn't have information
            if "don't have information" in response.lower():
                self.pending_handoff[session_key] = True
                self.conversation_history[session_key].append(f"AI: {response}")
                return False, response, 0.3
            else:
                self.conversation_history[session_key].append(f"AI: {response}")
                return False, response, 0.9
                
        except Exception as e:
            print(f"AI generation error: {e}")
            # Fallback to handoff offer
            self.pending_handoff[session_key] = True
            response = "I don't have information about that. I can connect you with our support representative if you want."
            self.conversation_history[session_key].append(f"AI: {response}")
            return False, response, 0.3
    
    def get_conversation_history(self, session_id: str = None) -> str:
        """Get formatted conversation history for a session"""
        session_key = session_id or 'default'
        if session_key in self.conversation_history:
            return "\n".join(self.conversation_history[session_key])
        return ""
        
