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
        """Monitor session with minimal polling for agent messages only"""
        last_message_id = 0
        
        while session_id in self.connections:
            try:
                # Check session status
                if not self.odoo_client.is_session_active(session_id):
                    await self.send_message(session_id, {
                        "type": "session_ended",
                        "message": "Agent has left the chat"
                    })
                    break
                
                # Get only agent messages (not visitor messages)
                messages = self.odoo_client.get_agent_messages_only(session_id, last_message_id)
                if messages:
                    for msg in messages:
                        await self.send_message(session_id, {
                            "type": "message",
                            "data": msg
                        })
                        last_message_id = max(last_message_id, msg['id'])
                
                await asyncio.sleep(2)  # Check every 2 seconds for agent messages only
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Monitor error for session {session_id}: {e}")
                await asyncio.sleep(5)
        
        self.disconnect(session_id)