import requests
import json
import asyncio
from typing import Dict, Any, Optional

class OdooClient:
    def __init__(self, url: str, db: str, username: str, password: str):
        self.url = url.rstrip('/')
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.session = requests.Session()
        self.operator_states = {}  # Track operator changes
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
                        "user_id": False,
                        "persisted": True
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
                                # Send the initial message as visitor
                                self.send_message_to_session(session_id, message, visitor_name)
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
    
    def send_message_to_session(self, session_id: int, message: str, author_name: str) -> bool:
        """Send message as visitor with instant notification"""
        try:
            if not self.is_session_active(session_id):
                print(f"Session {session_id} is not active, cannot send message")
                return False
            
            # Send message and trigger notification
            message_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "discuss.channel",
                    "method": "message_post",
                    "args": [session_id],
                    "kwargs": {
                        "body": message,
                        "message_type": "comment",
                        "author_id": False,
                        "email_from": f"{author_name} <visitor@livechat.com>"
                    }
                },
                "id": 3
            }
            
            response = self.session.post(f"{self.url}/web/dataset/call_kw", json=message_data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('result'):
                    message_id = result['result']
                    print(f"✅ Message sent to session {session_id}, ID: {message_id}")
                    
                    # Trigger bus notification for instant delivery
                    self._trigger_notification(session_id, message_id)
                    return True
            
            print(f"❌ Failed to send message to session {session_id}")
            return False
            
        except Exception as e:
            print(f"Error sending message: {e}")
            return False
    
    def _trigger_notification(self, session_id: int, message_id: int):
        """Trigger bus notification for instant message delivery"""
        try:
            # Method 1: Trigger channel notification
            notify_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "discuss.channel",
                    "method": "_broadcast",
                    "args": [session_id, ["discuss.channel", session_id]],
                    "kwargs": {}
                },
                "id": 4
            }
            
            response = self.session.post(f"{self.url}/web/dataset/call_kw", json=notify_data)
            if response.status_code == 200:
                print(f"⚡ Notification triggered for session {session_id}")
                return
            
            # Method 2: Update channel to trigger notification
            update_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "discuss.channel",
                    "method": "write",
                    "args": [[session_id], {"message_needaction_counter": 1}],
                    "kwargs": {}
                },
                "id": 5
            }
            
            self.session.post(f"{self.url}/web/dataset/call_kw", json=update_data)
            print(f"⚡ Channel updated for session {session_id}")
            
        except Exception as e:
            print(f"Error triggering notification: {e}")
    
    def is_session_active(self, session_id: int) -> bool:
        """Check if session is still active with comprehensive checks"""
        try:
            # Re-authenticate if needed
            if not self.uid:
                if not self.authenticate():
                    return False
            
            # Get comprehensive session data
            session_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "discuss.channel",
                    "method": "read",
                    "args": [[session_id], [
                        "livechat_status", 
                        "livechat_end_dt", 
                        "livechat_operator_id",
                        "channel_member_ids",
                        "is_member"
                    ]],
                    "kwargs": {}
                },
                "id": 8
            }
            
            response = self.session.post(f"{self.url}/web/dataset/call_kw", json=session_data)
            
            if response.status_code == 200:
                result = response.json()
                
                # Check for session expired error
                if result.get('error') and 'Session Expired' in str(result['error']):
                    # Re-authenticate and try again
                    if self.authenticate():
                        response = self.session.post(f"{self.url}/web/dataset/call_kw", json=session_data)
                        if response.status_code == 200:
                            result = response.json()
                
                if result.get('result') and len(result['result']) > 0:
                    channel_data = result['result'][0]
                    status = channel_data.get('livechat_status')
                    end_dt = channel_data.get('livechat_end_dt')
                    operator_id = channel_data.get('livechat_operator_id')
                    member_ids = channel_data.get('channel_member_ids', [])
                    
                    print(f"Session {session_id} active check - status: {status}, end_dt: {end_dt}, operator: {operator_id}, members: {len(member_ids)}")
                    
                    # Session is inactive if:
                    # 1. Status is closed/ended
                    # 2. Has end datetime  
                    # 3. No operator assigned (agent left)
                    # 4. Less than 2 members (visitor + agent)
                    if (status in ['closed', 'ended'] or end_dt or not operator_id or len(member_ids) < 2):
                        print(f"Session {session_id} is INACTIVE - status={status}, end_dt={end_dt}, operator={operator_id}, members={len(member_ids)}")
                        return False
                    
                    print(f"Session {session_id} is ACTIVE")
                    return True
            
            print(f"Session {session_id} - Cannot determine status, assuming inactive")
            return False  # Be conservative - assume inactive if we can't check
            
        except Exception as e:
            print(f"Error checking session status: {e}")
            return False  # Be conservative on error
    
    async def start_longpolling_listener(self, session_id: int, callback):
        """Start longpolling listener for real-time notifications"""
        last_message_id = 0
        
        while True:
            try:
                message_data = {
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {
                        "model": "mail.message",
                        "method": "search_read",
                        "args": [[
                            ["res_id", "=", session_id], 
                            ["model", "=", "discuss.channel"],
                            ["id", ">", last_message_id],
                            ["author_id", "!=", False]
                        ], ["id", "body", "author_id", "date", "email_from"]],
                        "kwargs": {"order": "date asc", "limit": 5}
                    },
                    "id": 6
                }
                
                response = self.session.post(f"{self.url}/web/dataset/call_kw", json=message_data)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get('result'):
                        for msg in result['result']:
                            # Skip visitor messages
                            if not (msg.get('email_from') and 'visitor@livechat.com' in msg['email_from']):
                                import re
                                clean_body = re.sub(r'<[^>]+>', '', msg['body'])
                                author_name = msg['author_id'][1] if isinstance(msg['author_id'], list) else 'Agent'
                                
                                await callback({
                                    'type': 'message',
                                    'data': {
                                        'id': msg['id'],
                                        'body': clean_body,
                                        'author': author_name,
                                        'date': msg['date']
                                    }
                                })
                                
                                last_message_id = max(last_message_id, msg['id'])
                
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"❌ Message check error for session {session_id}: {e}")
                await asyncio.sleep(3)
                continue
    
    def store_feedback(self, session_id: int, rating: str, comment: str = "") -> bool:
        """Store feedback for a chat session in Odoo"""
        try:
            feedback_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "discuss.channel",
                    "method": "message_post",
                    "args": [session_id],
                    "kwargs": {
                        "body": f"<p><strong>Customer Feedback:</strong> {rating.upper()}</p><p>{comment}</p>",
                        "message_type": "comment",
                        "subtype_xmlid": "mail.mt_note"
                    }
                },
                "id": 9
            }
            
            response = self.session.post(f"{self.url}/web/dataset/call_kw", json=feedback_data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('result'):
                    print(f"✅ Feedback stored for session {session_id}: {rating}")
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error storing feedback: {e}")
            return False