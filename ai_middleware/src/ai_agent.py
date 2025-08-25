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
        
    def load_knowledge_base(self, directory: str):
        """Load knowledge base from directory"""
        self.kb.load_from_directory(directory)
    
    def should_handoff(self, message: str, context: str = "") -> Tuple[bool, str, float]:
        """Determine if message should be handed off to human agent"""
        # Check for explicit human agent requests
        human_keywords = ['talk to support', 'speak to support', 'human agent', 'live agent', 'representative', 'talk to someone', 'speak to person', 'connect me to agent']
        message_lower = message.lower()
        if any(keyword in message_lower for keyword in human_keywords) or ('support' in message_lower and ('talk' in message_lower or 'speak' in message_lower)):
            return True, "I'll connect you with a human agent.", 0.0
        
        # Get relevant context from knowledge base
        relevant_docs = self.kb.search(message, top_k=3)
        
        # Handle greetings first
        greeting_words = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening', 'how are you', 'test', 'testing']
        if any(word in message.lower() for word in greeting_words):
            return False, "Hello! How can I help you today?", 0.9
        
        # Use knowledge base for known questions
        if relevant_docs and relevant_docs[0][1] > 0.4:
            kb_content = relevant_docs[0][0]
            # Extract answer from Q&A format
            if 'A:' in kb_content:
                answer = kb_content.split('A:')[1].strip()
                return False, answer, relevant_docs[0][1]
        
        # For unknown questions, offer handoff
        return True, "I'm sorry, I don't have information about that. Would you like me to connect you with our support representative?", 0.0
            
        except Exception as e:
            print(f"AI processing error: {e}")
            return True, "I'm having some technical difficulties. Let me connect you with a human agent.", 0.0