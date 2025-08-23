import os
from typing import Dict, Tuple, Optional
from .knowledge_base import KnowledgeBase

class AIAgent:
    def __init__(self, api_key: str, confidence_threshold: float = 0.7):
        self.api_key = api_key
        self.confidence_threshold = confidence_threshold
        self.kb = KnowledgeBase()
        
    def load_knowledge_base(self, directory: str):
        """Load knowledge base from directory"""
        self.kb.load_from_directory(directory)
    
    def should_handoff(self, message: str, context: str = "") -> Tuple[bool, str, float]:
        """Determine if message should be handed off to human agent"""
        # Check for explicit human agent requests first
        human_keywords = ['support', 'agent', 'human', 'help', 'talk to someone', 'representative']
        if any(keyword in message.lower() for keyword in human_keywords):
            return True, "I'll connect you with a human agent.", 0.0
        
        # Get relevant context from knowledge base
        relevant_docs = self.kb.search(message, top_k=3)
        
        # If we have good knowledge base matches, return the answer
        if relevant_docs and relevant_docs[0][1] >= 0.5:
            return False, relevant_docs[0][0], relevant_docs[0][1]
        
        # If we have some context, use AI to process it
        if relevant_docs:
            kb_context = "\n".join([doc for doc, score in relevant_docs if score > 0.2])
            
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.api_key)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": f"Answer the customer question using this context: {kb_context}"},
                        {"role": "user", "content": message}
                    ],
                    max_tokens=200,
                    temperature=0.3
                )
                
                ai_answer = response.choices[0].message.content.strip()
                return False, ai_answer, 0.8
                
            except Exception as e:
                print(f"AI processing error: {e}")
                # Fall back to knowledge base answer
                return False, relevant_docs[0][0], relevant_docs[0][1]
        
        # No good matches - handoff to human
        return True, "I need to connect you with a human agent for better assistance.", 0.0