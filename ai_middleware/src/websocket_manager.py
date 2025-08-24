"""
WebSocket connection manager
"""
import asyncio
import json
from typing import Dict
from fastapi import WebSocket

class WebSocketManager:
    def __init__(self, odoo_client):
        self.connections: Dict[int, WebSocket] = {}
        self.tasks: Dict[int, asyncio.Task] = {}
        self.odoo_client = odoo_client
    
    async def connect(self, websocket: WebSocket, session_id: int):
        """Accept WebSocket connection and start monitoring"""
        await websocket.accept()
        self.connections[session_id] = websocket
        
        # Start monitoring task
        task = asyncio.create_task(self._monitor_session(session_id))
        self.tasks[session_id] = task
        
        print(f"✅ WebSocket connected for session {session_id}")
    
    def disconnect(self, session_id: int):
        """Clean up connection and task"""
        if session_id in self.connections:
            del self.connections[session_id]
        
        if session_id in self.tasks:
            self.tasks[session_id].cancel()
            del self.tasks[session_id]
        
        print(f"🔌 WebSocket disconnected for session {session_id}")
    
    async def send_message(self, session_id: int, message: dict):
        """Send message to WebSocket client"""
        if session_id in self.connections:
            try:
                await self.connections[session_id].send_text(json.dumps(message))
                return True
            except Exception as e:
                print(f"❌ Failed to send WebSocket message: {e}")
                self.disconnect(session_id)
                return False
        return False
    
    async def _monitor_session(self, session_id: int):
        """Monitor session using Odoo's native WebSocket bus"""
        print(f"⚡ Starting WebSocket monitoring for session {session_id}")
        
        # Subscribe to Odoo's WebSocket bus for this channel
        odoo_ws = await self.odoo_client.connect_to_odoo_websocket(session_id)
        
        if not odoo_ws:
            print(f"❌ Failed to connect to Odoo WebSocket for session {session_id}")
            self.disconnect(session_id)
            return
        
        try:
            while session_id in self.connections:
                try:
                    # Listen for real-time messages from Odoo WebSocket
                    message = await odoo_ws.recv()
                    data = json.loads(message)
                    
                    if data.get('type') == 'mail.message':
                        # New message from agent
                        msg_data = data.get('payload', {})
                        if msg_data.get('author_id') and 'visitor@livechat.com' not in str(msg_data.get('email_from', '')):
                            await self.send_message(session_id, {
                                "type": "message",
                                "data": {
                                    'id': msg_data.get('id'),
                                    'body': msg_data.get('body', '').replace('<p>', '').replace('</p>', ''),
                                    'author': msg_data.get('author_id', [None, 'Agent'])[1] if isinstance(msg_data.get('author_id'), list) else 'Agent',
                                    'date': msg_data.get('date')
                                }
                            })
                    
                    elif data.get('type') == 'channel.ended':
                        await self.send_message(session_id, {
                            "type": "session_ended",
                            "message": "Agent has left the chat"
                        })
                        break
                        
                except asyncio.TimeoutError:
                    # Check if session is still active periodically
                    if not self.odoo_client.is_session_active(session_id):
                        await self.send_message(session_id, {
                            "type": "session_ended",
                            "message": "Agent has left the chat"
                        })
                        break
                        
                except Exception as e:
                    print(f"❌ WebSocket message error for session {session_id}: {e}")
                    await asyncio.sleep(1)
                    
        except Exception as e:
            print(f"❌ WebSocket monitoring error for session {session_id}: {e}")
        finally:
            if odoo_ws:
                await odoo_ws.close()
            self.disconnect(session_id)