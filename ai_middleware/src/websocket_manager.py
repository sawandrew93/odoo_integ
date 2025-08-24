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
        """Monitor session using Odoo's longpolling for real-time notifications"""
        print(f"⚡ Starting longpolling monitoring for session {session_id}")
        
        async def message_callback(data):
            """Callback for new messages from Odoo"""
            if session_id in self.connections:
                await self.send_message(session_id, data)
        
        # Start longpolling listener
        longpoll_task = asyncio.create_task(
            self.odoo_client.start_longpolling_listener(session_id, message_callback)
        )
        
        # Monitor session status separately
        try:
            while session_id in self.connections:
                # Check session status every 30 seconds
                await asyncio.sleep(30)
                
                if not self.odoo_client.is_session_active(session_id):
                    await self.send_message(session_id, {
                        "type": "session_ended",
                        "message": "Agent has left the chat"
                    })
                    break
                    
        except Exception as e:
            print(f"❌ Session monitoring error for {session_id}: {e}")
        finally:
            longpoll_task.cancel()
            self.disconnect(session_id)