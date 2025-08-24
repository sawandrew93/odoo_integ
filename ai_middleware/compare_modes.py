#!/usr/bin/env python3
"""
Compare WebSocket vs Polling performance
"""
import time
import requests
import asyncio
import websockets
import json

API_BASE = 'http://localhost:8000'
WS_BASE = 'ws://localhost:8000'

def measure_polling_latency(session_id, iterations=5):
    """Measure polling response time"""
    print(f"\n📊 Measuring polling latency for session {session_id}...")
    
    latencies = []
    for i in range(iterations):
        start_time = time.time()
        try:
            response = requests.get(f'{API_BASE}/messages/{session_id}')
            if response.status_code == 200:
                end_time = time.time()
                latency = (end_time - start_time) * 1000  # Convert to ms
                latencies.append(latency)
                print(f"  Poll {i+1}: {latency:.2f}ms")
            else:
                print(f"  Poll {i+1}: Failed ({response.status_code})")
        except Exception as e:
            print(f"  Poll {i+1}: Error - {e}")
        
        time.sleep(1)  # Wait between polls
    
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        print(f"📈 Average polling latency: {avg_latency:.2f}ms")
        return avg_latency
    return None

async def measure_websocket_latency(session_id, iterations=5):
    """Measure WebSocket response time"""
    print(f"\n⚡ Measuring WebSocket latency for session {session_id}...")
    
    try:
        async with websockets.connect(f'{WS_BASE}/ws/{session_id}') as websocket:
            latencies = []
            
            for i in range(iterations):
                start_time = time.time()
                try:
                    await websocket.send(json.dumps({'type': 'ping'}))
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    end_time = time.time()
                    
                    data = json.loads(response)
                    if data.get('type') == 'pong':
                        latency = (end_time - start_time) * 1000  # Convert to ms
                        latencies.append(latency)
                        print(f"  Ping {i+1}: {latency:.2f}ms")
                    else:
                        print(f"  Ping {i+1}: Unexpected response")
                        
                except asyncio.TimeoutError:
                    print(f"  Ping {i+1}: Timeout")
                except Exception as e:
                    print(f"  Ping {i+1}: Error - {e}")
                
                await asyncio.sleep(1)  # Wait between pings
            
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                print(f"⚡ Average WebSocket latency: {avg_latency:.2f}ms")
                return avg_latency
                
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        return None

async def main():
    """Compare both modes"""
    print("🔍 PERFORMANCE COMPARISON: WebSocket vs Polling")
    print("=" * 60)
    
    # Create a test session
    print("\n1. Creating test session...")
    response = requests.post(f'{API_BASE}/chat', json={
        'message': 'Performance test',
        'visitor_name': 'Performance Tester'
    })
    
    if response.status_code != 200:
        print("❌ Failed to create test session")
        return
    
    data = response.json()
    if not data.get('handoff_needed') or not data.get('odoo_session_id'):
        print("❌ No session created for performance test")
        return
    
    session_id = data['odoo_session_id']
    print(f"✅ Test session created: {session_id}")
    
    # Test WebSocket performance
    ws_latency = await measure_websocket_latency(session_id)
    
    # Test polling performance  
    polling_latency = measure_polling_latency(session_id)
    
    # Show comparison
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE RESULTS")
    print("=" * 60)
    
    if ws_latency and polling_latency:
        print(f"WebSocket Average:  {ws_latency:.2f}ms")
        print(f"Polling Average:    {polling_latency:.2f}ms")
        
        if ws_latency < polling_latency:
            improvement = ((polling_latency - ws_latency) / polling_latency) * 100
            print(f"\n🚀 WebSocket is {improvement:.1f}% faster than polling!")
        else:
            print(f"\n📡 Polling performed similarly to WebSocket")
            
        print(f"\n💡 RECOMMENDATIONS:")
        if ws_latency < 100:
            print("   ✅ WebSocket is working well - use widget_websocket.html")
        else:
            print("   ⚠️ WebSocket latency is high - polling might be more reliable")
            
    elif ws_latency:
        print(f"WebSocket Average:  {ws_latency:.2f}ms")
        print("Polling:           Failed")
        print("\n✅ Use WebSocket mode (widget_websocket.html)")
        
    elif polling_latency:
        print("WebSocket:         Failed") 
        print(f"Polling Average:   {polling_latency:.2f}ms")
        print("\n📡 Use polling mode - WebSocket not supported")
        
    else:
        print("❌ Both modes failed - check server configuration")

if __name__ == "__main__":
    asyncio.run(main())