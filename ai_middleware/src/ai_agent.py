import openai
from typing import Dict, Tuple, Optional
from .knowledge_base import KnowledgeBase

class AIAgent:
    def __init__(self, api_key: str, confidence_threshold: float = 0.7):
        openai.api_key = api_key
        self.confidence_threshold = confidence_threshold
        self.kb = KnowledgeBase()
        
    def load_knowledge_base(self, directory: str):
        """Load knowledge base from directory"""
        self.kb.load_from_directory(directory)
    
    def should_handoff(self, message: str, context: str = "") -> Tuple[bool, str, float]:
        """Determine if message should be handed off to human agent"""
        # Get relevant context from knowledge base
        relevant_docs = self.kb.search(message, top_k=3)
        kb_context = "\n".join([doc for doc, score in relevant_docs if score > 0.3])
        
        # Create prompt for AI decision
        system_prompt = f"""You are an AI assistant for customer support. Based on the knowledge base context below, determine if you can confidently answer the customer's question.

Knowledge Base Context:
{kb_context}

Additional Context:
{context}

Rules:
1. If you can provide a complete, accurate answer based on the knowledge base, respond with the answer
2. If the question requires human judgment, account access, or complex troubleshooting, indicate handoff needed
3. If you're uncertain about any part of the answer, indicate handoff needed

Respond in this format:
CONFIDENCE: [0.0-1.0]
HANDOFF: [YES/NO]
RESPONSE: [your response or "HANDOFF_NEEDED"]"""

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            ai_response = response.choices[0].message.content
            
            # Parse response
            lines = ai_response.strip().split('\n')
            confidence = 0.0
            handoff_needed = True
            ai_answer = "I need to connect you with a human agent."
            
            for line in lines:
                if line.startswith('CONFIDENCE:'):
                    try:
                        confidence = float(line.split(':')[1].strip())
                    except:
                        confidence = 0.0
                elif line.startswith('HANDOFF:'):
                    handoff_needed = line.split(':')[1].strip().upper() == 'YES'
                elif line.startswith('RESPONSE:'):
                    ai_answer = line.split(':', 1)[1].strip()
            
            # Override handoff decision based on confidence threshold
            if confidence < self.confidence_threshold:
                handoff_needed = True
                ai_answer = "I need to connect you with a human agent for better assistance."
            
            return handoff_needed, ai_answer, confidence
            
        except Exception as e:
            print(f"AI processing error: {e}")
            return True, "I need to connect you with a human agent.", 0.0