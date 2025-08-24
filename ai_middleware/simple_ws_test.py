#!/usr/bin/env python3
"""
Simple WebSocket server test
"""
from fastapi import FastAPI, WebSocket
import uvicorn
import asyncio

app = FastAPI()

@app.websocket("/test")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Hello WebSocket!")
    await websocket.close()

@app.get("/")
async def root():
    return {"message": "WebSocket test server running"}

if __name__ == "__main__":
    print("🧪 Testing WebSocket support...")
    try:
        uvicorn.run(app, host="0.0.0.0", port=8081)
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        print("Run: python fix_websocket.py")