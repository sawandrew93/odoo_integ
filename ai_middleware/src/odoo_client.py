import requests
import json
from typing import Dict, Any, Optional

class OdooClient:
    def __init__(self, url: str, db: str, username: str, password: str):
        self.url = url.rstrip('/')
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.session_id = None
        
    def authenticate(self) -> bool:
        """Authenticate with Odoo and get session"""
        auth_data = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "common",
                "method": "authenticate",
                "args": [self.db, self.username, self.password, {}]
            },
            "id": 1
        }
        
        response = requests.post(f"{self.url}/jsonrpc", json=auth_data)
        result = response.json()
        
        if result.get('result'):
            self.uid = result['result']
            return True
        return False
    
    def create_live_chat_session(self, visitor_name: str, message: str) -> Optional[int]:
        """Create a new live chat session in Odoo"""
        if not self.uid:
            if not self.authenticate():
                return None
                
        create_data = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    self.db, self.uid, self.password,
                    'im_livechat.channel', 'create_session',
                    [], {
                        'anonymous_name': visitor_name,
                        'previous_operator_id': False,
                        'user_id': False,
                        'country_id': False
                    }
                ]
            },
            "id": 2
        }
        
        response = requests.post(f"{self.url}/jsonrpc", json=create_data)
        result = response.json()
        
        if result.get('result'):
            session_id = result['result'].get('id')
            if session_id:
                self.send_message_to_session(session_id, message, visitor_name)
            return session_id
        return None
    
    def send_message_to_session(self, session_id: int, message: str, author_name: str):
        """Send message to existing live chat session"""
        message_data = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    self.db, self.uid, self.password,
                    'mail.channel', 'message_post',
                    [session_id], {
                        'body': message,
                        'message_type': 'comment',
                        'author_id': False,
                        'email_from': f"{author_name} <visitor@example.com>"
                    }
                ]
            },
            "id": 3
        }
        
        requests.post(f"{self.url}/jsonrpc", json=message_data)