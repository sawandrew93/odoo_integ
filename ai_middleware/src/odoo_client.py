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
        """Send message as visitor with instant Odoo notification"""
        try:
            if not self.is_session_active(session_id):
                print(f"Session {session_id} is not active, cannot send message")
                return False
            
            # Send message using Odoo's livechat method for instant notification
            message_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "im_livechat.channel",
                    "method": "send_visitor_message",
                    "args": [1, session_id, message, author_name],
                    "kwargs": {}
                },
                "id": 3
            }
            
            response = self.session.post(f"{self.url}/web/dataset/call_kw", json=message_data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('result') is not False:
                    print(f"⚡ Instant message sent to session {session_id}")
                    return True
            
            # Fallback to regular message_post
            fallback_data = {
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
                "id": 4
            }
            
            fallback_response = self.session.post(f"{self.url}/web/dataset/call_kw", json=fallback_data)
            
            if fallback_response.status_code == 200:
                fallback_result = fallback_response.json()
                if fallback_result.get('result'):
                    print(f"✅ Message sent to session {session_id} (fallback)")
                    return True
            
            print(f"❌ Failed to send message to session {session_id}")
            return False
            
        except Exception as e:
            print(f"Error sending message: {e}")
            return False
    


    
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
        last_notification_id = 0
        
        while True:
            try:
                # Use Odoo's longpolling for real-time notifications
                longpoll_data = {
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {
                        "channels": [f"discuss.channel_{session_id}"],
                        "last": last_notification_id,
                        "options": {"bus_inactivity": 60000}
                    },
                    "id": 10
                }
                
                # Long polling request (waits for notifications)
                response = self.session.post(
                    f"{self.url}/longpolling/poll", 
                    json=longpoll_data, 
                    timeout=65  # Slightly longer than bus_inactivity
                )
                
                if response.status_code == 200:
                    result = response.json()
                    notifications = result.get('result', [])
                    
                    for notification in notifications:
                        if len(notification) >= 3:
                            channel, message_data, notif_id = notification[0], notification[1], notification[2]
                            
                            if f"discuss.channel_{session_id}" in str(channel):
                                if isinstance(message_data, dict):
                                    # Check if it's a new message from agent
                                    if (message_data.get('type') == 'mail.message' and 
                                        message_data.get('author_id') and 
                                        'visitor@livechat.com' not in str(message_data.get('email_from', ''))):
                                        
                                        await callback({
                                            'type': 'message',
                                            'data': {
                                                'id': message_data.get('id'),
                                                'body': message_data.get('body', '').replace('<p>', '').replace('</p>', ''),
                                                'author': message_data.get('author_id', [None, 'Agent'])[1] if isinstance(message_data.get('author_id'), list) else 'Agent',
                                                'date': message_data.get('date')
                                            }
                                        })
                            
                            last_notification_id = max(last_notification_id, notif_id)
                
                await asyncio.sleep(0.1)  # Brief pause before next longpoll
                
            except asyncio.TimeoutError:
                # Timeout is normal for longpolling, just continue
                continue
            except Exception as e:
                print(f"❌ Longpolling error for session {session_id}: {e}")
                await asyncio.sleep(2)
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