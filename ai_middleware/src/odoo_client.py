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
        self.session = requests.Session()
        # Set proper headers for Odoo Online
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (compatible; AI-Middleware/1.0)'
        })
        
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
        
        # Try channel ID 1 first, then 2
        for channel_id in [1, 2]:
            print(f"Attempting to create session for channel {channel_id} with visitor {visitor_name}")
            
            try:
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
                
                response = self.session.post(f"{self.url}/im_livechat/get_session", json=rpc_data)
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        print(f"Live chat response: {result}")
                        
                        if result.get('result') and result['result'] != False:
                            session_data = result['result']
                            session_id = session_data.get('channel_id')
                            if session_id:
                                print(f"✅ Live chat session created! ID: {session_id}")
                                return session_id
                    except json.JSONDecodeError:
                        print(f"Non-JSON response for channel {channel_id}: {response.text[:200]}")
                        continue
                else:
                    print(f"HTTP {response.status_code} for channel {channel_id}")
                    
            except Exception as e:
                print(f"Error with channel {channel_id}: {e}")
                continue
        
        print("❌ All channels failed")
        return None
    
    def send_message_to_session(self, session_id: int, message: str, author_name: str):
        """Send message to existing live chat session"""
        try:
            message_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "channel_id": session_id,
                    "message": message
                },
                "id": 3
            }
            
            response = self.session.post(f"{self.url}/im_livechat/send_message", json=message_data)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"Message send result: {result}")
                    
                    if result.get('result'):
                        print(f"✅ Message sent successfully to session {session_id}")
                    else:
                        print(f"❌ Failed to send message: {result}")
                except json.JSONDecodeError:
                    print(f"Non-JSON response when sending message: {response.text[:200]}")
            else:
                print(f"HTTP {response.status_code} when sending message")
            
        except Exception as e:
            print(f"Error sending message: {e}")