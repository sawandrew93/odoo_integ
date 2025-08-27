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
        
        agent_joined = False
        session_ended = False
        
        async def message_callback(data):
            """Callback for new messages from Odoo"""
            nonlocal agent_joined, session_ended
            
            if session_id in self.connections:
                if data.get('type') == 'message':
                    # Check if this is first agent message (not visitor)
                    author = data['data']['author']
                    if not agent_joined and author != 'Website Visitor':
                        agent_joined = True
                        # Extract name only (after comma if exists)
                        display_name = author.split(', ')[-1] if ', ' in author else author
                        setattr(self, f'_agent_name_{session_id}', display_name)
                        await self.send_message(session_id, {
                            "type": "agent_joined",
                            "message": f"{display_name} joined the chat"
                        })
                    
                    # Update message author to show only name
                    if author != 'Website Visitor' and ', ' in author:
                        data['data']['author'] = author.split(', ')[-1]
                    
                    await self.send_message(session_id, data)
                    
                elif data.get('type') == 'session_ended':
                    session_ended = True
                    await self.send_message(session_id, data)
                    # Show feedback after session ends
                    await asyncio.sleep(2)
                    await self.send_message(session_id, {
                        "type": "show_feedback",
                        "message": "Please rate this conversation"
                    })
        
        # Start longpolling listener
        longpoll_task = asyncio.create_task(
            self.odoo_client.start_longpolling_listener(session_id, message_callback)
        )
        
        # Monitor session status separately
        try:
            while session_id in self.connections and not session_ended:
                # Check session status every 10 seconds for faster detection
                await asyncio.sleep(10)
                
                if not self.odoo_client.is_session_active(session_id):
                    # Get the last known agent name for the left message
                    agent_name = getattr(self, f'_agent_name_{session_id}', 'Agent')
                    await message_callback({
                        "type": "session_ended",
                        "message": f"{agent_name} left the channel"
                    })
                    break
                    
        except Exception as e:
            print(f"❌ Session monitoring error for {session_id}: {e}")
        finally:
            longpoll_task.cancel()
            self.disconnect(session_id)