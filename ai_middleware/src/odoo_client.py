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
        """Send message as visitor to the live chat session"""
        try:
            # First check if session is still active with comprehensive check
            if not self.is_session_active(session_id):
                print(f"Session {session_id} is not active, cannot send message")
                return False
            
            # Send message as visitor (not as authenticated user)
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
                        "author_id": False,  # No author = visitor message
                        "email_from": f"{author_name} <visitor@livechat.com>"
                    }
                },
                "id": 3
            }
            
            response = self.session.post(f"{self.url}/web/dataset/call_kw", json=message_data)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"Message send result: {result}")
                    
                    if result.get('result'):
                        print(f"✅ Message sent successfully to session {session_id}")
                        # Trigger notification to agent
                        self.notify_agent(session_id)
                        return True
                    else:
                        print(f"❌ Failed to send message: {result}")
                        return False
                except json.JSONDecodeError:
                    print(f"Non-JSON response when sending message: {response.text[:200]}")
                    return False
            else:
                print(f"HTTP {response.status_code} when sending message")
                return False
            
        except Exception as e:
            print(f"Error sending message: {e}")
            return False
    
    def notify_agent(self, session_id: int):
        """Send notification to agent about new message"""
        try:
            notify_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "discuss.channel",
                    "method": "_notify_thread",
                    "args": [session_id],
                    "kwargs": {}
                },
                "id": 4
            }
            
            response = self.session.post(f"{self.url}/web/dataset/call_kw", json=notify_data)
            if response.status_code == 200:
                print(f"✅ Agent notification sent for session {session_id}")
            
        except Exception as e:
            print(f"Error notifying agent: {e}")
    
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
                    if (status in ['closed', 'ended'] or 
                        end_dt or 
                        not operator_id or 
                        len(member_ids) <= 1):  # Only visitor left
                        session_ended = True
                        print(f"Session {session_id} has ended - Reason: status={status}, end_dt={end_dt}, operator={operator_id}, members={len(member_ids)}")
            
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
                        # Double-check with agent status if session appears active
                        agent_status = self.check_agent_status(session_id)
                        if not agent_status["active"]:
                            print(f"Agent disconnected for session {session_id}: {agent_status['reason']}")
                            messages.append({
                                'id': 999998,
                                'body': 'AGENT_DISCONNECTED',
                                'author': 'System',
                                'date': ''
                            })
                    
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
                    
                    # Session is inactive if any of these conditions are true:
                    # 1. Status is closed/ended
                    # 2. Has end datetime
                    # 3. No operator assigned (agent left)
                    # 4. Only visitor left in channel (member count <= 1)
                    if (status in ['closed', 'ended'] or 
                        end_dt or 
                        not operator_id or 
                        len(member_ids) <= 1):
                        print(f"Session {session_id} is INACTIVE - status={status}, end_dt={end_dt}, operator={operator_id}, members={len(member_ids)}")
                        return False
                    
                    print(f"Session {session_id} is ACTIVE")
                    return True
            
            print(f"Session {session_id} - Cannot determine status, assuming inactive")
            return False  # Be conservative - assume inactive if we can't check
            
        except Exception as e:
            print(f"Error checking session status: {e}")
            return False  # Be conservative on error
    
    def check_agent_status(self, session_id: int) -> dict:
        """Check detailed agent status for the session"""
        try:
            if not self.uid:
                if not self.authenticate():
                    return {"active": False, "reason": "auth_failed"}
            
            # Get channel members with their online status
            member_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "discuss.channel.member",
                    "method": "search_read",
                    "args": [[["channel_id", "=", session_id]], [
                        "partner_id", 
                        "is_online", 
                        "last_seen_dt",
                        "create_date"
                    ]],
                    "kwargs": {}
                },
                "id": 9
            }
            
            response = self.session.post(f"{self.url}/web/dataset/call_kw", json=member_data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('result'):
                    members = result['result']
                    agent_online = False
                    visitor_count = 0
                    
                    for member in members:
                        partner_id = member.get('partner_id')
                        is_online = member.get('is_online', False)
                        
                        if partner_id and isinstance(partner_id, list):
                            partner_name = partner_id[1]
                            # Check if this is an agent (not visitor)
                            if 'visitor' not in partner_name.lower() and 'anonymous' not in partner_name.lower():
                                if is_online:
                                    agent_online = True
                                print(f"Agent {partner_name} online: {is_online}")
                            else:
                                visitor_count += 1
                    
                    return {
                        "active": agent_online,
                        "reason": "agent_offline" if not agent_online else "active",
                        "member_count": len(members),
                        "visitor_count": visitor_count
                    }
            
            return {"active": False, "reason": "no_data"}
            
        except Exception as e:
            print(f"Error checking agent status: {e}")
            return {"active": False, "reason": "error"}