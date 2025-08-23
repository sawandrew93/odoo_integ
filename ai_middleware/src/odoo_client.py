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
            # Use the web livechat init endpoint
            init_data = {
                "params": {
                    "channel_id": 1,  # Default channel
                    "anonymous_name": visitor_name
                }
            }
            
            response = self.session.post(
                f"{self.url}/im_livechat/init",
                json=init_data,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result and 'uuid' in result:
                    session_uuid = result['uuid']
                    print(f"✅ Live chat session created! UUID: {session_uuid}")
                    
                    # Send initial message
                    self.send_message_to_livechat(session_uuid, message, visitor_name)
                    return session_uuid
            
            print(f"❌ Failed to create session: {response.text}")
                    
        except Exception as e:
            print(f"Odoo session creation error: {e}")
            
        return None
    
    def send_message_to_livechat(self, session_uuid: str, message: str, author_name: str):
        """Send message to livechat session"""
        try:
            message_data = {
                "params": {
                    "uuid": session_uuid,
                    "message_content": message
                }
            }
            
            response = self.session.post(
                f"{self.url}/im_livechat/send_message",
                json=message_data,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                print(f"✅ Message sent to livechat {session_uuid}")
            else:
                print(f"❌ Failed to send message: {response.text}")
            
        except Exception as e:
            print(f"Error sending message: {e}")
    
    def send_message_to_session(self, session_id, message: str, author_name: str):
        """Backward compatibility wrapper"""
        self.send_message_to_livechat(session_id, message, author_name)