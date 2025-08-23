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
                "db": self.db,
                "login": self.username,
                "password": self.password
            },
            "id": 1
        }
        
        try:
            response = requests.post(f"{self.url}/web/session/authenticate", json=auth_data)
            result = response.json()
            print(f"Auth response: {result}")
            
            if result.get('result') and result['result'].get('uid'):
                self.uid = result['result']['uid']
                self.session_id = response.cookies.get('session_id')
                return True
        except Exception as e:
            print(f"Auth error: {e}")
            
        return False
    
    def create_live_chat_session(self, visitor_name: str, message: str) -> Optional[int]:
        """Create a new live chat session in Odoo"""
        if not self.uid:
            if not self.authenticate():
                return None
        
        # Get live chat channel (ID 2 from your script)
        channel_id = 2
        
        try:
            # Create session via im_livechat.channel
            create_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "im_livechat.channel",
                    "method": "get_mail_channel",
                    "args": [channel_id],
                    "kwargs": {
                        'anonymous_name': visitor_name,
                        'previous_operator_id': False,
                        'country_id': False
                    }
                },
                "id": 2
            }
            
            response = requests.post(f"{self.url}/web/dataset/call_kw", json=create_data)
            result = response.json()
            print(f"Live chat response: {result}")
            
            if result.get('result'):
                session_data = result['result']
                session_id = session_data.get('id')
                if session_id:
                    self.send_message_to_session(session_id, message, visitor_name)
                    return session_id
                    
        except Exception as e:
            print(f"Odoo session creation error: {e}")
            
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