#!/usr/bin/env python3
"""
Test script to verify WebSocket functionality with Odoo Online
"""
import asyncio
import websockets
import json
import requests
import time

API_BASE = 'http://localhost:8000'
WS_BASE = 'ws://localhost:8000'

async def test_websocket_connection():
    """Test WebSocket connection and message flow"""
    print("🧪 Testing WebSocket functionality...")
    
    # Step 1: Create a chat session
    print("\n1. Creating chat session...")
    response = requests.post(f'{API_BASE}/chat', json={
        'message': 'I need help with my account',
        'visitor_name': 'Test User'
    })
    
    if response.status_code != 200:
        print(f"❌ Failed to create session: {response.status_code}")
        return False
    
    data = response.json()
    if not data.get('handoff_needed') or not data.get('odoo_session_id'):
        print("❌ Session not created or no handoff needed")
        return False
    
    session_id = data['odoo_session_id']
    print(f"✅ Session created: {session_id}")
    
    # Step 2: Test WebSocket connection
    print(f"\n2. Testing WebSocket connection to session {session_id}...")
    
    try:
        async with websockets.connect(f'{WS_BASE}/ws/{session_id}') as websocket:
            print("✅ WebSocket connected successfully")
            
            # Step 3: Send ping and wait for pong
            print("\n3. Testing ping/pong...")
            await websocket.send(json.dumps({'type': 'ping'}))
            
            # Wait for pong response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                pong_data = json.loads(response)
                if pong_data.get('type') == 'pong':
                    print("✅ Ping/pong successful")
                else:
                    print(f"⚠️ Unexpected response: {pong_data}")
            except asyncio.TimeoutError:
                print("⚠️ No pong response received (timeout)")
            
            # Step 4: Send a message and monitor for responses
            print(f"\n4. Sending message to session {session_id}...")
            msg_response = requests.post(f'{API_BASE}/chat', json={
                'message': 'Hello from test',
                'visitor_name': 'Test User',
                'session_id': str(session_id)
            })
            
            if msg_response.status_code == 200:
                print("✅ Message sent successfully")
            else:
                print(f"❌ Failed to send message: {msg_response.status_code}")
            
            # Step 5: Listen for WebSocket messages
            print("\n5. Listening for WebSocket messages (10 seconds)...")
            try:
                for i in range(5):  # Listen for 10 seconds
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        ws_data = json.loads(message)
                        print(f"📨 Received: {ws_data}")
                    except asyncio.TimeoutError:
                        print(f"⏱️ No message received in iteration {i+1}")
                        continue
                        
            except Exception as e:
                print(f"❌ Error listening for messages: {e}")
            
            print("✅ WebSocket test completed")
            return True
            
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        return False

async def test_polling_fallback():
    """Test polling fallback functionality"""
    print("\n🔄 Testing polling fallback...")
    
    # Create session
    response = requests.post(f'{API_BASE}/chat', json={
        'message': 'Test polling mode',
        'visitor_name': 'Polling Test User'
    })
    
    if response.status_code != 200:
        print(f"❌ Failed to create session for polling test")
        return False
    
    data = response.json()
    if not data.get('handoff_needed') or not data.get('odoo_session_id'):
        print("❌ Polling test session not created")
        return False
    
    session_id = data['odoo_session_id']
    print(f"✅ Polling test session created: {session_id}")
    
    # Test polling endpoints
    print("\n📡 Testing polling endpoints...")
    
    # Test session status
    status_response = requests.get(f'{API_BASE}/session/{session_id}/status')
    if status_response.status_code == 200:
        status_data = status_response.json()
        print(f"✅ Session status: {status_data}")
    else:
        print(f"❌ Failed to get session status: {status_response.status_code}")
    
    # Test messages endpoint
    messages_response = requests.get(f'{API_BASE}/messages/{session_id}')
    if messages_response.status_code == 200:
        messages_data = messages_response.json()
        print(f"✅ Messages endpoint working: {len(messages_data.get('messages', []))} messages")
    else:
        print(f"❌ Failed to get messages: {messages_response.status_code}")
    
    return True

def test_health_check():
    """Test basic health check"""
    print("\n🏥 Testing health check...")
    try:
        response = requests.get(f'{API_BASE}/health')
        if response.status_code == 200:
            print(f"✅ Health check passed: {response.json()}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Starting WebSocket and Polling Tests")
    print("=" * 50)
    
    # Test 1: Health check
    health_ok = test_health_check()
    
    if not health_ok:
        print("\n❌ Server not responding. Make sure the server is running:")
        print("   python run.py")
        return
    
    # Test 2: WebSocket functionality
    ws_ok = await test_websocket_connection()
    
    # Test 3: Polling fallback
    polling_ok = await test_polling_fallback()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Health Check: {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"WebSocket:    {'✅ PASS' if ws_ok else '❌ FAIL'}")
    print(f"Polling:      {'✅ PASS' if polling_ok else '❌ FAIL'}")
    
    if ws_ok:
        print("\n🎉 WebSocket is working! Your Odoo Online supports WebSocket connections.")
        print("   Use widget_websocket.html for the best experience.")
    else:
        print("\n⚠️ WebSocket failed. This is normal for some Odoo Online instances.")
        print("   The system will automatically fall back to polling mode.")
        print("   Use widget_websocket.html - it will auto-detect and use polling.")

if __name__ == "__main__":
    asyncio.run(main())