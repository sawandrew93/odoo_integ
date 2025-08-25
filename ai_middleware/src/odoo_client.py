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
        
        # First, get available live chat channels
        try:
            channels_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "im_livechat.channel",
                    "method": "search_read",
                    "args": [[], ["id", "name", "user_ids"]],
                    "kwargs": {}
                },
                "id": 1
            }
            
            response = self.session.post(f"{self.url}/web/dataset/call_kw", json=channels_data)
            if response.status_code == 200:
                result = response.json()
                if result.get('result'):
                    channels = result['result']
                    print(f"Available live chat channels: {channels}")
                    
                    # Try each available channel
                    for channel in channels:
                        channel_id = channel['id']
                        if not channel.get('user_ids'):  # Skip channels with no operators
                            continue
                            
                        print(f"Attempting to create session for channel {channel_id} ({channel['name']})")
                        
                        # Try the updated endpoint
                        rpc_data = {
                            "jsonrpc": "2.0",
                            "method": "call",
                            "params": {
                                "channel_id": channel_id,
                                "anonymous_name": visitor_name
                            },
                            "id": 2
                        }
                        
                        session_response = self.session.post(f"{self.url}/im_livechat/get_session", json=rpc_data)
                        
                        if session_response.status_code == 200:
                            session_result = session_response.json()
                            print(f"Live chat response: {session_result}")
                            
                            if session_result.get('result') and session_result['result'] != False:
                                session_data = session_result['result']
                                session_id = session_data.get('channel_id')
                                visitor_uuid = session_data.get('uuid')
                                if session_id:
                                    print(f"✅ Live chat session created! ID: {session_id}, UUID: {visitor_uuid}")
                                    # Send the initial message using standard method
                                    self.send_message_to_session(session_id, message, visitor_name)
                                    return session_id
                else:
                    print("No live chat channels found")
        except Exception as e:
            print(f"Error getting channels: {e}")
        
        print("❌ Failed to create live chat session")
        return None
    

    def send_message_to_session(self, session_id: int, message: str, author_name: str) -> bool:
        """Send message as visitor with instant notification"""
        try:
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
    


    
    def get_session_messages(self, session_id: int):
        """Get messages from live chat session"""
        try:
            # Check comprehensive session status
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
                "id": 6
            }
            
            session_response = self.session.post(f"{self.url}/web/dataset/call_kw", json=session_data)
            session_ended = False
            
            if session_response.status_code == 200:
                session_result = session_response.json()
                print(f"Session status check: {session_result}")
                if session_result.get('result') and len(session_result['result']) > 0:
                    channel_data = session_result['result'][0]
                    status = channel_data.get('livechat_status')
                    end_dt = channel_data.get('livechat_end_dt')
                    operator_id = channel_data.get('livechat_operator_id')
                    member_ids = channel_data.get('channel_member_ids', [])
                    
                    print(f"Session {session_id} - status: {status}, end_dt: {end_dt}, operator: {operator_id}, members: {len(member_ids)}")
                    
                    # Check multiple conditions for session end
                    if (status in ['closed', 'ended'] or end_dt):
                        session_ended = True
                        print(f"Session {session_id} has ended - Reason: status={status}, end_dt={end_dt}")
            
            # Get messages
            message_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "mail.message",
                    "method": "search_read",
                    "args": [[["res_id", "=", session_id], ["model", "=", "discuss.channel"]], ["id", "body", "author_id", "date", "email_from"]],
                    "kwargs": {
                        "order": "date desc",
                        "limit": 10
                    }
                },
                "id": 5
            }
            
            response = self.session.post(f"{self.url}/web/dataset/call_kw", json=message_data)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('result'):
                    messages = []
                    for msg in result['result']:
                        # Only return agent messages (messages with author_id)
                        if msg.get('author_id') and msg['author_id'] != False:
                            # Skip visitor messages (check if it's not from visitor email)
                            if not (msg.get('email_from') and 'visitor@livechat.com' in msg['email_from']):
                                # Strip HTML tags from body
                                import re
                                clean_body = re.sub(r'<[^>]+>', '', msg['body'])
                                messages.append({
                                    'id': msg['id'],
                                    'body': clean_body,
                                    'author': msg['author_id'][1] if isinstance(msg['author_id'], list) else 'Agent',
                                    'date': msg['date']
                                })
                    
                    # Add session ended indicator if needed
                    if session_ended:
                        print(f"Adding SESSION_ENDED message for session {session_id}")
                        messages.append({
                            'id': 999999,
                            'body': 'SESSION_ENDED',
                            'author': 'System',
                            'date': ''
                        })
                    else:
                        # Check if operator was removed (agent left)
                        previous_operator = self.operator_states.get(session_id)
                        current_operator = operator_id
                        
                        # Only check for disconnect if we have a previous state
                        if previous_operator is not None:
                            if previous_operator and not current_operator:
                                print(f"Agent left session {session_id} - operator removed")
                                messages.append({
                                    'id': 999998,
                                    'body': 'AGENT_DISCONNECTED',
                                    'author': 'System',
                                    'date': ''
                                })
                        
                        # Update operator state
                        self.operator_states[session_id] = current_operator
                    
                    return messages
            
            return []
            
        except Exception as e:
            print(f"Error getting messages: {e}")
            return []
    
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
                    if (status in ['closed', 'ended'] or end_dt or not operator_id):
                        print(f"Session {session_id} is INACTIVE - status={status}, end_dt={end_dt}, operator={operator_id}")
                        return False
                    
                    print(f"Session {session_id} is ACTIVE")
                    return True
            
            print(f"Session {session_id} - Cannot determine status, assuming inactive")
            return False  # Be conservative - assume inactive if we can't check
            
        except Exception as e:
            print(f"Error checking session status: {e}")
            return False  # Be conservative on error
    
    def check_agent_status(self, session_id: int) -> dict:
        """Check if agent is still in the session"""
        try:
            if not self.uid:
                if not self.authenticate():
                    return {"active": False, "reason": "auth_failed"}
            
            # Get session data to check operator
            session_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "discuss.channel",
                    "method": "read",
                    "args": [[session_id], ["livechat_operator_id", "livechat_status", "livechat_end_dt"]],
                    "kwargs": {}
                },
                "id": 9
            }
            
            response = self.session.post(f"{self.url}/web/dataset/call_kw", json=session_data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('result') and len(result['result']) > 0:
                    data = result['result'][0]
                    operator_id = data.get('livechat_operator_id')
                    status = data.get('livechat_status')
                    end_dt = data.get('livechat_end_dt')
                    
                    # Agent is active if operator assigned and session not ended
                    agent_active = bool(operator_id) and status not in ['closed', 'ended'] and not end_dt
                    
                    return {
                        "active": agent_active,
                        "reason": "active" if agent_active else "agent_left",
                        "operator_id": operator_id
                    }
            
            return {"active": False, "reason": "no_data"}
            
        except Exception as e:
            print(f"Error checking agent status: {e}")
            return {"active": False, "reason": "error"}
    
    async def start_longpolling_listener(self, session_id: int, callback):
        """Start longpolling listener for real-time notifications"""
        last_message_id = 0
        
        while True:
            try:
                # Simple approach: check for new agent messages
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
                                
                                # Check if agent left
                                if 'left the channel' in clean_body or 'left the conversation' in clean_body:
                                    await callback({
                                        'type': 'session_ended',
                                        'message': f'{author_name} ended the session'
                                    })
                                else:
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
                
                await asyncio.sleep(1)  # Check every second for agent messages
                
            except Exception as e:
                print(f"❌ Message check error for session {session_id}: {e}")
                await asyncio.sleep(3)
                continue
    
    def store_feedback(self, session_id: int, rating: str, comment: str = "") -> bool:
        """Store feedback for a chat session in Odoo"""
        try:
            # Add note to the channel with feedback
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