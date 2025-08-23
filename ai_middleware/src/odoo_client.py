import requests
import json
import os
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
        
        try:
            # First get available live chat channels
            channels_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "im_livechat.channel",
                    "method": "search_read",
                    "args": [[], ["id", "name"]],
                    "kwargs": {}
                },
                "id": 1
            }
            
            response = self.session.post(f"{self.url}/web/dataset/call_kw", json=channels_data)
            channels_result = response.json()
            
            if not channels_result.get('result'):
                print("No live chat channels found")
                return None
                
            channel_id = channels_result['result'][0]['id']
            print(f"Using channel ID: {channel_id}")
            
            # Create mail channel for live chat
            create_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "mail.channel",
                    "method": "create",
                    "args": [{
                        "name": f"Live Chat with {visitor_name}",
                        "channel_type": "livechat",
                        "livechat_channel_id": channel_id,
                        "anonymous_name": visitor_name
                    }],
                    "kwargs": {}
                },
                "id": 2
            }
            
            response = self.session.post(f"{self.url}/web/dataset/call_kw", json=create_data)
            result = response.json()
            
            if result.get('result'):
                session_id = result['result']
                print(f"✅ Live chat session created! ID: {session_id}")
                
                # Send the initial message
                self.send_message_to_session(session_id, message, visitor_name)
                return session_id
            else:
                print(f"❌ Failed to create session: {result}")
                    
        except Exception as e:
            print(f"Odoo session creation error: {e}")
            
        return None
    
    def send_message_to_session(self, session_id: int, message: str, author_name: str):
        """Send message to existing live chat session"""
        try:
            message_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "mail.channel",
                    "method": "message_post",
                    "args": [session_id],
                    "kwargs": {
                        "body": message,
                        "message_type": "comment",
                        "author_id": False,
                        "email_from": f"{author_name} <visitor@example.com>"
                    }
                },
                "id": 3
            }
            
            response = self.session.post(f"{self.url}/web/dataset/call_kw", json=message_data)
            result = response.json()
            
            if result.get('result'):
                print(f"✅ Message sent successfully to session {session_id}")
            else:
                print(f"❌ Failed to send message: {result}")
            
        except Exception as e:
            print(f"Error sending message: {e}")