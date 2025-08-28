import requests
import json
import asyncio
import os
import base64
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
                        download_url = f"https://odoo.andrewdemo.online/download/{att['id']}"
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
                        "body": f"<p><strong>Customer Feedback:</strong> {rating}/5 stars</p><p>{comment}</p>",
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
                    print(f"✅ Feedback stored for session {session_id}: {rating}/5")
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error storing feedback: {e}")
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
                    message_body = message if message else f"📎 {file_name}"
                    
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