#!/usr/bin/env python3
"""
Check which connection mode is being used
"""
import requests
import time

def check_logs():
    """Analyze server behavior to determine connection mode"""
    print("🔍 Checking connection mode...")
    print("\nLook at your server logs for these patterns:")
    print("\n✅ WebSocket mode indicators:")
    print("   - 'WebSocket /ws/XXX [accepted]'")
    print("   - '✅ WebSocket connected for session XXX'")
    print("   - 'INFO: connection open'")
    
    print("\n📡 Polling mode indicators:")
    print("   - 'GET /session/XXX/status'")
    print("   - 'GET /messages/XXX'")
    print("   - Repeated every 3 seconds")
    
    print("\n🔄 Both modes running:")
    print("   - You'll see BOTH patterns above")
    print("   - This means WebSocket is working but polling is also active")
    
    print("\n💡 To confirm WebSocket is working:")
    print("   1. Open widget_websocket.html")
    print("   2. Check the connection status bar")
    print("   3. Should show 'Real-time connected' (green)")

if __name__ == "__main__":
    check_logs()