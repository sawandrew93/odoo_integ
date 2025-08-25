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
        human_keywords = ['agent', 'human', 'talk to someone', 'representative', 'speak to person']
        if any(keyword in message.lower() for keyword in human_keywords):
            return True, "I'll connect you with a human agent.", 0.0
        
        # Get relevant context from knowledge base
        relevant_docs = self.kb.search(message, top_k=3)
        
        # Use AI to generate response based on context or general support
        try:
            if relevant_docs and relevant_docs[0][1] > 0.3:
                kb_context = "\n".join([doc for doc, score in relevant_docs[:2] if score > 0.3])
                prompt = f"You are a helpful customer support agent. Answer the customer's question using the provided context. Be friendly and concise.\n\nContext: {kb_context}\n\nCustomer: {message}\n\nResponse:"
            else:
                prompt = f"You are a helpful customer support agent. The customer said: '{message}'. If this is a greeting, respond warmly. If it's a question you cannot answer with confidence, say you'll connect them with a human agent. Be friendly and concise.\n\nResponse:"
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=150,
                    temperature=0.4
                )
            )
            
            ai_answer = response.text.strip()
            
            # Check if AI suggests handoff
            handoff_phrases = ['connect you with', 'human agent', 'transfer you', 'speak with someone']
            if any(phrase in ai_answer.lower() for phrase in handoff_phrases):
                return True, "Let me connect you with one of our human agents who can better assist you.", 0.0
            
            # If no relevant docs and not a greeting, consider handoff
            if not relevant_docs or relevant_docs[0][1] < 0.3:
                greeting_words = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening']
                if not any(word in message.lower() for word in greeting_words):
                    return True, "I'd like to connect you with one of our human agents who can better help with your specific question.", 0.0
            
            return False, ai_answer, 0.8
            
        except Exception as e:
            print(f"AI processing error: {e}")
            return True, "I'm having some technical difficulties. Let me connect you with a human agent.", 0.0