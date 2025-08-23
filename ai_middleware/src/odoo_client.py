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
        self.session = requests.Session()  # Maintain session cookies
        
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
            response = self.session.post(f"{self.url}/web/session/authenticate", json=auth_data)
            result = response.json()
            print(f"Auth response: {result}")
            
            if result.get('result') and result['result'].get('uid'):
                self.uid = result['result']['uid']
                return True
        except Exception as e:
            print(f"Auth error: {e}")
            
        return False
    
    def create_live_chat_session(self, visitor_name: str, message: str) -> Optional[int]:
        """Create a new live chat session in Odoo"""
        if not self.uid:
            if not self.authenticate():
                return None
        
        # Use the live chat web controller (channel ID 2 from your script)
        channel_id = 2
        
        try:
            # Create session via JSON-RPC
            rpc_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "channel_id": channel_id,
                    "anonymous_name": visitor_name,
                    "previous_operator_id": False,
                    "country_id": False
                },
                "id": 2
            }
            
            response = self.session.post(
                f"{self.url}/im_livechat/get_session", 
                json=rpc_data,
                headers={'Content-Type': 'application/json'}
            )
            
            result = response.json()
            print(f"Live chat response: {result}")
            
            if result.get('result'):
                session_data = result['result']
                session_id = session_data.get('channel_id')
                if session_id:
                    print(f"✅ Live chat session created! ID: {session_id}")
                    # Send initial message
                    self.send_message_to_session(session_id, message, visitor_name)
                    return session_id
                    
        except Exception as e:
            print(f"Odoo session creation error: {e}")
            
        return None
    
    def send_message_to_session(self, session_id: int, message: str, author_name: str):
        """Send message to existing live chat session"""
        try:
            # Use JSON-RPC for message posting
            rpc_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "discuss.channel",
                    "method": "message_post",
                    "args": [session_id],
                    "kwargs": {
                        "body": message,
                        "message_type": "comment"
                    }
                },
                "id": 3
            }
            
            response = self.session.post(
                f"{self.url}/web/dataset/call_kw",
                json=rpc_data
            )
            
            print(f"Message send response: {response.status_code}")
            
        except Exception as e:
            print(f"Error sending message: {e}")