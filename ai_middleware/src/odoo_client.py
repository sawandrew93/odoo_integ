import requests
import json
import asyncio
import os
import base64
from typing import Dict, Any, Optional

class OdooClient:
    def __init__(self, url: str, db: str, api_key: str):
        self.url = url.rstrip('/')
        self.db = db
        self.api_key = api_key
        self.uid = None
        self.session = requests.Session()
        self.operator_states = {}  # Track operator changes
        
        # Set basic headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (compatible; AI-Middleware/1.0)'
        })
        
    def authenticate(self) -> bool:
        """Authenticate with Odoo using API key"""
        
        if not self.api_key:
            print("❌ No API key provided")
            return False
            
        # For API key authentication, we need the username from environment
        username = os.getenv('ODOO_USERNAME')
        if not username:
            print("❌ Username required for API key authentication")
            return False
            
        try:
            # Odoo API key authentication: username as login, API key as password
            auth_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "service": "common",
                    "method": "authenticate",
                    "args": [self.db, username, self.api_key, {}]
                },
                "id": 1
            }
            
            response = self.session.post(f"{self.url}/jsonrpc", json=auth_data)
            result = response.json()
            
            print(f"API key auth response: {result}")
            
            if response.status_code == 200 and result.get('result') and result['result'] != False:
                self.uid = result['result']
                print(f"✅ API key authentication successful, UID: {self.uid}")
                return True
            else:
                print(f"❌ API key authentication failed: {result.get('error', result)}")
                return False
                
        except Exception as e:
            print(f"❌ API key auth error: {e}")
            return False
    
    def get_available_channels(self) -> list:
        """Get all available live chat channels"""
        try:
            channel_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "im_livechat.channel",
                    "method": "search_read",
                    "args": [[], ["id", "name", "user_ids"]],
                    "kwargs": {}
                },
                "id": 15
            }
            
            response = self.session.post(f"{self.url}/web/dataset/call_kw", json=channel_data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('result'):
                    channels = result['result']
                    print(f"📋 Found {len(channels)} live chat channels:")
                    for ch in channels:
                        print(f"  - Channel {ch['id']}: {ch['name']} (operators: {len(ch.get('user_ids', []))})")
                    return [ch['id'] for ch in channels]
            
            return [1, 2]  # Fallback
            
        except Exception as e:
            print(f"Error getting channels: {e}")
            return [1, 2]  # Fallback
    
    def create_live_chat_session(self, visitor_name: str, message: str) -> Optional[int]:
        """Create a new live chat session in Odoo"""
        if not self.uid:
            if not self.authenticate():
                return None
        
        # Get all available channels dynamically
        available_channels = self.get_available_channels()
        
        # Try each channel
        for channel_id in available_channels:
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
                            
                            # Extract session ID from discuss.channel array or channel_id
                            session_id = None
                            
                            # Method 1: Try to get from discuss.channel array
                            if 'discuss.channel' in session_data:
                                channels = session_data['discuss.channel']
                                if channels and len(channels) > 0:
                                    session_id = channels[0]['id']
                            
                            # Method 2: Try to get from channel_id field
                            if not session_id and 'channel_id' in session_data:
                                session_id = session_data['channel_id']
                            
                            if session_id:
                                print(f"✅ Live chat session created! ID: {session_id}")
                                
                                # Send the initial message as visitor (skip session check for new sessions)
                                self._send_initial_message(session_id, message, visitor_name)
                                return session_id
                            else:
                                print(f"❌ Could not extract session ID from response")
                                continue
                    except json.JSONDecodeError:
                        print(f"Non-JSON response for channel {channel_id}: {response.text[:200]}")
                        continue
                else:
                    print(f"HTTP {response.status_code} for channel {channel_id}")
                    
            except Exception as e:
                print(f"Error with channel {channel_id}: {e}")
                continue
        
        print(f"❌ All {len(available_channels)} channels failed")
        return None
    
    def _send_initial_message(self, session_id: int, message: str, author_name: str) -> bool:
        """Send initial message to newly created session (skips active check)"""
        try:
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
                    print(f"✅ Initial message sent to session {session_id}, ID: {message_id}")
                    return True
            
            print(f"❌ Failed to send initial message to session {session_id}")
            return False
            
        except Exception as e:
            print(f"Error sending initial message: {e}")
            return False
    
    def send_message_to_session(self, session_id: int, message: str, author_name: str) -> bool:
        """Send message as visitor with instant notification"""
        try:
            # Skip session check for system messages
            if author_name != "System" and not self.is_session_active(session_id):
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
        """Check if session is still active"""
        try:
            if not self.uid:
                if not self.authenticate():
                    return False
            
            session_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "discuss.channel",
                    "method": "read",
                    "args": [[session_id], ["state", "livechat_active", "livechat_end_dt"]],
                    "kwargs": {}
                },
                "id": 8
            }
            
            response = self.session.post(f"{self.url}/web/dataset/call_kw", json=session_data)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('result') and len(result['result']) > 0:
                    channel_data = result['result'][0]
                    state = channel_data.get('state')
                    livechat_active = channel_data.get('livechat_active')
                    end_dt = channel_data.get('livechat_end_dt')
                    
                    # Session is active if state is 'open' and livechat_active is True and no end_dt
                    is_active = (state == 'open' and livechat_active and not end_dt)
                    print(f"Session {session_id} - state: {state}, active: {livechat_active}, end_dt: {end_dt} → {'ACTIVE' if is_active else 'INACTIVE'}")
                    return is_active
            
            print(f"Session {session_id} - Cannot determine status, assuming active for new sessions")
            return True  # Assume active for newly created sessions
            
        except Exception as e:
            print(f"Error checking session status: {e}")
            return True  # Assume active on error for new sessions
    
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
                            ["author_id", "!=", False],
                            ["message_type", "=", "comment"],
                            ["subtype_id.name", "!=", "Note"]
                        ], ["id", "body", "author_id", "date", "email_from", "attachment_ids", "message_type", "subtype_id"]],
                        "kwargs": {"order": "date asc", "limit": 5}
                    },
                    "id": 6
                }
                
                response = self.session.post(f"{self.url}/web/dataset/call_kw", json=message_data)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get('result'):
                        for msg in result['result']:
                            # Skip visitor messages and feedback messages
                            if not (msg.get('email_from') and 'visitor@livechat.com' in msg['email_from']):
                                # Skip feedback messages (internal notes)
                                if 'Customer Feedback:' in msg.get('body', ''):
                                    last_message_id = max(last_message_id, msg['id'])
                                    continue
                                    
                                import re
                                clean_body = re.sub(r'<[^>]+>', '', msg['body'])
                                author_name = msg['author_id'][1] if isinstance(msg['author_id'], list) else 'Agent'
                                
                                # Handle attachments
                                attachments = []
                                if msg.get('attachment_ids'):
                                    print(f"Found attachment_ids: {msg['attachment_ids']}")
                                    attachments = self._get_attachments_sync(msg['attachment_ids'])
                                    print(f"Fetched {len(attachments)} attachments: {[att['name'] for att in attachments]}")
                                
                                # Detect message type
                                message_type = 'text'
                                if attachments:
                                    for att in attachments:
                                        if att['mimetype'].startswith('audio/'):
                                            message_type = 'voice'
                                            break
                                        elif att['mimetype'].startswith('image/') and 'gif' in att['mimetype']:
                                            message_type = 'gif'
                                            break
                                
                                await callback({
                                    'type': 'message',
                                    'data': {
                                        'id': msg['id'],
                                        'body': clean_body,
                                        'author': author_name,
                                        'date': msg['date'],
                                        'attachments': attachments,
                                        'message_type': message_type
                                    }
                                })
                                
                                last_message_id = max(last_message_id, msg['id'])
                
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"❌ Message check error for session {session_id}: {e}")
                await asyncio.sleep(3)
                continue
    
    def _get_attachments_sync(self, attachment_ids):
        """Fetch attachment details from Odoo (synchronous version)"""
        if not attachment_ids:
            return []
        
        try:
            attachment_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "ir.attachment",
                    "method": "read",
                    "args": [attachment_ids, ["id", "name", "mimetype", "file_size", "datas"]],
                    "kwargs": {}
                },
                "id": 10
            }
            
            response = self.session.post(f"{self.url}/web/dataset/call_kw", json=attachment_data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('result'):
                    attachments = []
                    for att in result['result']:
                        # Create download URL through middleware proxy
                        download_url = f"https://ai.andrewdemo.online/download/{att['id']}"
                        attachments.append({
                            'id': att['id'],
                            'name': att['name'],
                            'mimetype': att.get('mimetype', 'application/octet-stream'),
                            'size': att.get('file_size', 0),
                            'download_url': download_url
                        })
                    return attachments
        except Exception as e:
            print(f"Error fetching attachments: {e}")
            import traceback
            traceback.print_exc()
        
        return []
    
    def get_session_messages(self, session_id: int) -> list:
        """Get messages from a live chat session"""
        try:
            message_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "mail.message",
                    "method": "search_read",
                    "args": [[
                        ["res_id", "=", session_id], 
                        ["model", "=", "discuss.channel"]
                    ], ["id", "body", "author_id", "date"]],
                    "kwargs": {"order": "date asc"}
                },
                "id": 10
            }
            
            response = self.session.post(f"{self.url}/web/dataset/call_kw", json=message_data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('result'):
                    messages = []
                    for msg in result['result']:
                        import re
                        clean_body = re.sub(r'<[^>]+>', '', msg['body']) if msg['body'] else ''
                        author_name = msg['author_id'][1] if isinstance(msg['author_id'], list) else 'System'
                        
                        messages.append({
                            'id': msg['id'],
                            'body': clean_body,
                            'author': author_name,
                            'date': msg['date']
                        })
                    return messages
            
            return []
            
        except Exception as e:
            print(f"Error getting messages: {e}")
            return []
    
    def store_feedback(self, session_id: int, rating: int, comment: str = "") -> bool:
        """Store feedback for a chat session in Odoo (internal only)"""
        try:
            # Create feedback text
            feedback_text = f"Customer Feedback: {rating}/5 stars"
            if comment.strip():
                feedback_text += f" - {comment}"
            
            # Store as internal note (not visible to agents in chat)
            feedback_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "discuss.channel",
                    "method": "message_post",
                    "args": [session_id],
                    "kwargs": {
                        "body": feedback_text,
                        "message_type": "notification",
                        "subtype_xmlid": "mail.mt_note",
                        "internal": True
                    }
                },
                "id": 9
            }
            
            response = self.session.post(f"{self.url}/web/dataset/call_kw", json=feedback_data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('result'):
                    print(f"✅ Feedback stored internally for session {session_id}: {rating}/5")
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error storing feedback: {e}")
            return False
    
    def end_live_chat_session(self, session_id: int, message: str) -> bool:
        """End live chat session properly"""
        try:
            if not self.uid:
                if not self.authenticate():
                    return False
            
            # Send final message
            self.send_message_to_session(session_id, message, "System")
            
            # Close the session using Odoo's proper method
            close_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "im_livechat.channel",
                    "method": "close_session",
                    "args": [session_id],
                    "kwargs": {}
                },
                "id": 13
            }
            
            response = self.session.post(f"{self.url}/web/dataset/call_kw", json=close_data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('result'):
                    print(f"✅ Session {session_id} closed")
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error ending session: {e}")
            return False
    
    def send_file_to_session(self, session_id: int, file_name: str, file_content: bytes, content_type: str, message: str = "") -> bool:
        """Send file attachment to Odoo live chat session"""
        try:
            if not self.uid:
                if not self.authenticate():
                    return False
            
            # Create attachment in Odoo
            import base64
            file_data = base64.b64encode(file_content).decode('utf-8')
            
            attachment_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "ir.attachment",
                    "method": "create",
                    "args": [{
                        "name": file_name,
                        "datas": file_data,
                        "res_model": "discuss.channel",
                        "res_id": session_id,
                        "mimetype": content_type
                    }],
                    "kwargs": {}
                },
                "id": 11
            }
            
            response = self.session.post(f"{self.url}/web/dataset/call_kw", json=attachment_data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('result'):
                    attachment_id = result['result']
                    
                    # Send message with attachment
                    message_body = message if message else file_name
                    
                    message_data = {
                        "jsonrpc": "2.0",
                        "method": "call",
                        "params": {
                            "model": "discuss.channel",
                            "method": "message_post",
                            "args": [session_id],
                            "kwargs": {
                                "body": message_body,
                                "message_type": "comment",
                                "attachment_ids": [attachment_id],
                                "author_id": False,
                                "email_from": "Website Visitor <visitor@livechat.com>"
                            }
                        },
                        "id": 12
                    }
                    
                    msg_response = self.session.post(f"{self.url}/web/dataset/call_kw", json=message_data)
                    
                    if msg_response.status_code == 200:
                        msg_result = msg_response.json()
                        if msg_result.get('result'):
                            print(f"✅ File {file_name} sent to session {session_id}")
                            return True
            
            return False
            
        except Exception as e:
            print(f"Error sending file: {e}")
            return False