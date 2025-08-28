import os
from typing import Dict, Tuple, Optional, List
import google.generativeai as genai
from .knowledge_base import KnowledgeBase
import re
from enum import Enum

class ConversationState(Enum):
    GREETING = "greeting"
    HELPING = "helping"
    PENDING_HANDOFF = "pending_handoff"
    ESCALATED = "escalated"

class AIAgent:
    def __init__(self, api_key: str, confidence_threshold: float = 0.7, supabase_url: str = None, supabase_key: str = None):
        self.api_key = api_key
        self.confidence_threshold = confidence_threshold
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        self.kb = KnowledgeBase(api_key, supabase_url, supabase_key)
        
        self.system_message = """You are a friendly customer support assistant. Be conversational and helpful while answering questions using only the provided knowledge base content."""
        
        self.conversation_states = {}
        self.conversation_history = {}
        self.user_context = {}
        
        # Enhanced patterns
        self.greeting_patterns = [
            r'\b(hi|hello|hey|good\s+(morning|afternoon|evening))\b',
            r'^(hi|hello|hey)$',
            r'how\s+are\s+you'
        ]
        
        # Removed regex patterns - now using AI for handoff detection
        
        self.frustration_patterns = [
            r'\b(frustrated|annoyed|angry|upset)\b',
            r'this\s+(sucks|is\s+terrible|doesn\'t\s+work)',
            r'waste\s+of\s+time'
        ]
    
    def should_handoff(self, message: str, context: str = "", session_id: str = None) -> Tuple[bool, str, float]:
        """Enhanced decision making for handoffs with better context awareness"""
        message_lower = message.lower().strip()
        session_key = session_id or 'default'
        
        # Initialize session data
        if session_key not in self.conversation_history:
            self.conversation_history[session_key] = []
            self.conversation_states[session_key] = ConversationState.GREETING
            self.user_context[session_key] = {'attempts': 0, 'topics': set()}
        
        self.conversation_history[session_key].append(f"User: {message}")
        current_state = self.conversation_states[session_key]
        
        # Handle pending handoff responses
        if current_state == ConversationState.PENDING_HANDOFF:
            return self._handle_handoff_response(message_lower, session_key)
        
        # Use AI to detect handoff intent
        if self._ai_detect_handoff_intent(message):
            response = "I'll connect you with one of our support representatives right away."
            self.conversation_history[session_key].append(f"AI: {response}")
            return True, response, 0.0
        
        # Check for frustration and auto-escalate
        if self._detect_frustration(message_lower):
            self.user_context[session_key]['attempts'] += 1
            if self.user_context[session_key]['attempts'] >= 2:
                response = "I understand this might be frustrating. Let me connect you with our support team who can better assist you."
                self.conversation_states[session_key] = ConversationState.ESCALATED
                self.conversation_history[session_key].append(f"AI: {response}")
                return True, response, 0.0
        
        # Handle greetings
        if self._is_greeting(message_lower) and current_state == ConversationState.GREETING:
            response = self._generate_greeting_response()
            self.conversation_states[session_key] = ConversationState.HELPING
            self.conversation_history[session_key].append(f"AI: {response}")
            return False, response, 0.95
        
        # Generate AI response for questions
        return self._generate_ai_response(message, session_key)
    
    def _is_greeting(self, message: str) -> bool:
        return any(re.search(pattern, message, re.IGNORECASE) for pattern in self.greeting_patterns)
    
    def _ai_detect_handoff_intent(self, message: str) -> bool:
        """Use AI to intelligently detect handoff requests"""
        try:
            prompt = f"""Analyze this user message and determine if they want to talk to a human agent/support representative.

User message: "{message}"

Respond with only "YES" if they want human support, or "NO" if they don't.

Examples:
- "connect me with agent" → YES
- "I want to talk to someone" → YES  
- "please get me human help" → YES
- "this is not working" → NO
- "what are your hours" → NO
- "how do I reset password" → NO

Answer:"""
            
            response = self.model.generate_content(prompt)
            result = response.text.strip().upper()
            print(f"Handoff intent detection: '{message}' → {result}")
            return result == "YES"
        except Exception as e:
            print(f"Error in AI handoff detection: {e}")
            # Fallback to simple keyword check
            return any(word in message.lower() for word in ['human', 'agent', 'support', 'connect me', 'talk to someone'])
    
    def _detect_frustration(self, message: str) -> bool:
        return any(re.search(pattern, message, re.IGNORECASE) for pattern in self.frustration_patterns)
    
    def _generate_greeting_response(self) -> str:
        import random
        greetings = [
            "Hello! I'm here to help you with any questions you might have. What can I assist you with today?",
            "Hi there! How can I help you today?",
            "Hello! I'm your AI assistant. What would you like to know?"
        ]
        return random.choice(greetings)
    
    def _handle_handoff_response(self, message: str, session_key: str) -> Tuple[bool, str, float]:
        positive = ['yes', 'okay', 'ok', 'sure', 'please', 'yeah', 'connect me']
        negative = ['no', 'not now', 'later', 'continue']
        
        if any(word in message for word in positive):
            self.conversation_states[session_key] = ConversationState.ESCALATED
            response = "Perfect! I'm connecting you with a human agent now."
            self.conversation_history[session_key].append(f"AI: {response}")
            return True, response, 0.0
        elif any(word in message for word in negative):
            self.conversation_states[session_key] = ConversationState.HELPING
            response = "No problem! I'm still here to help. What else can I assist you with?"
            self.conversation_history[session_key].append(f"AI: {response}")
            return False, response, 0.9
        else:
            response = "Would you like me to connect you with a human agent? Please say 'yes' to connect or 'no' to continue."
            self.conversation_history[session_key].append(f"AI: {response}")
            return False, response, 0.5
    
    def _generate_ai_response(self, message: str, session_key: str) -> Tuple[bool, str, float]:
        try:
            # Search knowledge base
            relevant_docs = self.kb.search(message, top_k=5)
            print(f"Found {len(relevant_docs)} relevant documents for: {message}")
            
            # Calculate confidence based on document relevance
            confidence = self._calculate_confidence(relevant_docs)
            
            if confidence < 0.3 or not relevant_docs:
                response = self._generate_no_info_response()
                self.conversation_states[session_key] = ConversationState.PENDING_HANDOFF
                self.conversation_history[session_key].append(f"AI: {response}")
                return False, response, confidence
            
            # Build context
            knowledge_context = "\n\n".join([doc['content'] for doc in relevant_docs])
            conversation_context = self._build_conversation_context(session_key)
            
            # Generate response
            prompt = f"""You are a friendly customer support assistant. Answer naturally and conversationally.

Recent conversation:
{conversation_context}

Knowledge base information:
{knowledge_context}

User question: {message}

Instructions:
- Answer using the knowledge base information when available
- Be conversational and helpful
- Don't mention "knowledge base" - speak naturally
- Keep responses concise but complete
- If you don't have information about the topic, say "I don't have information about that. Would you like me to connect you with our support representative?"

Response:"""
            
            ai_response = self.model.generate_content(prompt)
            response = ai_response.text.strip()
            
            # Check if AI says it doesn't have information and offer handoff
            if any(phrase in response.lower() for phrase in ["don't have", "no information", "not sure", "can't help"]):
                if "connect" not in response.lower():
                    response += " Would you like me to connect you with our support representative?"
                self.conversation_states[session_key] = ConversationState.PENDING_HANDOFF
                self.conversation_history[session_key].append(f"AI: {response}")
                return False, response, 0.3
            
            # Post-process response
            response = re.sub(r'\bknowledge base\b', 'our information', response, flags=re.IGNORECASE)
            
            self.conversation_history[session_key].append(f"AI: {response}")
            return False, response, confidence
            
        except Exception as e:
            print(f"AI generation error: {e}")
            response = "I'm having trouble right now. Would you like me to connect you with our support team?"
            self.conversation_states[session_key] = ConversationState.PENDING_HANDOFF
            self.conversation_history[session_key].append(f"AI: {response}")
            return False, response, 0.2
    
    def _calculate_confidence(self, relevant_docs: List[dict]) -> float:
        if not relevant_docs:
            return 0.0
        max_score = max(doc.get('score', 0) for doc in relevant_docs)
        normalized_score = (max_score + 1) / 2
        if len(relevant_docs) >= 3 and normalized_score > 0.6:
            normalized_score = min(0.95, normalized_score + 0.1)
        return normalized_score
    
    def _generate_no_info_response(self) -> str:
        import random
        responses = [
            "I don't have specific information about that. Would you like me to connect you with our support team?",
            "That's not covered in my available information. Shall I connect you with a human agent?",
            "I don't have details on that topic. Our support team can provide more help. Would you like me to connect you?"
        ]
        return random.choice(responses)
    
    def _build_conversation_context(self, session_key: str) -> str:
        if session_key in self.conversation_history:
            recent_history = self.conversation_history[session_key][-4:]
            return "\n".join(recent_history)
        return ""
    
    def get_conversation_history(self, session_id: str = None) -> str:
        """Get formatted conversation history for a session"""
        session_key = session_id or 'default'
        if session_key in self.conversation_history:
            return "\n".join(self.conversation_history[session_key])
        return ""
    
    def get_conversation_summary(self, session_id: str = None) -> Dict:
        """Get comprehensive conversation summary"""
        session_key = session_id or 'default'
        return {
            'history': self.get_conversation_history(session_key),
            'state': self.conversation_states.get(session_key, ConversationState.GREETING).value,
            'context': self.user_context.get(session_key, {}),
            'message_count': len(self.conversation_history.get(session_key, []))
        }
    
    def reset_session(self, session_id: str = None):
        """Reset conversation state for a session"""
        session_key = session_id or 'default'
        for storage in [self.conversation_history, self.conversation_states, self.user_context]:
            if session_key in storage:
                del storage[session_key]
        
