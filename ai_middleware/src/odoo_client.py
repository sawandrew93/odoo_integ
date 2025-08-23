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
                    "country_id": False,
                    "user_id": False
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
            
            if result.get('result') and result['result'] != False:
                session_data = result['result']
                session_id = session_data.get('channel_id')
                if session_id:
                    print(f"✅ Live chat session created! ID: {session_id}")
                    # Don't send initial message - let the agent see the handoff request
                    return session_id
            else:
                print(f"❌ Live chat creation failed: {result.get('result')}")
                print("This might mean no agents are available or channel is not properly configured")
                    
        except Exception as e:
            print(f"Odoo session creation error: {e}")
            
        return None
    
    def send_message_to_session(self, session_id: int, message: str, author_name: str):
        """Send message to existing live chat session"""
        try:
            # Send message via live chat endpoint
            message_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "channel_id": session_id,
                    "message": message
                },
                "id": 3
            }
            
            response = self.session.post(
                f"{self.url}/im_livechat/send_message",
                json=message_data
            )
            
            result = response.json()
            print(f"Message send result: {result}")
            
            if result.get('result'):
                print(f"✅ Message sent successfully to session {session_id}")
            else:
                print(f"❌ Failed to send message: {result}")
            
        except Exception as e:
            print(f"Error sending message: {e}")