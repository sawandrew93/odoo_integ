#!/usr/bin/env python3
import os
import time
from dotenv import load_dotenv
from src.odoo_client import OdooClient

load_dotenv()

def test_agent_disconnect_detection():
    client = OdooClient(
        url=os.getenv('ODOO_URL'),
        db=os.getenv('ODOO_DB'), 
        username=os.getenv('ODOO_USERNAME'),
        password=os.getenv('ODOO_PASSWORD')
    )
    
    print("Testing agent disconnect detection...")
    
    # Test authentication
    if not client.authenticate():
        print("❌ Authentication failed")
        return
    
    print(f"✅ Authentication successful! UID: {client.uid}")
    
    # Create a test session
    session_id = client.create_live_chat_session("Test User", "Hello, testing agent disconnect detection")
    if not session_id:
        print("❌ Failed to create live chat session")
        return
    
    print(f"✅ Live chat session created! ID: {session_id}")
    print("\n🔄 Now manually join as agent in Odoo and then leave the session...")
    print("This script will monitor the session status every 3 seconds")
    print("Press Ctrl+C to stop monitoring\n")
    
    try:
        while True:
            # Check basic session status
            is_active = client.is_session_active(session_id)
            
            # Check detailed agent status
            agent_status = client.check_agent_status(session_id)
            
            # Get messages (which also checks for disconnection)
            messages = client.get_session_messages(session_id)
            
            print(f"Session {session_id}:")
            print(f"  - Session Active: {is_active}")
            print(f"  - Agent Online: {agent_status['active']}")
            print(f"  - Reason: {agent_status['reason']}")
            print(f"  - Member Count: {agent_status.get('member_count', 'N/A')}")
            print(f"  - Messages Count: {len(messages)}")
            
            # Check for system messages
            for msg in messages:
                if msg['body'] in ['SESSION_ENDED', 'AGENT_DISCONNECTED']:
                    print(f"  🚨 DETECTED: {msg['body']}")
            
            if not is_active or not agent_status['active']:
                print(f"\n🎯 AGENT DISCONNECT DETECTED!")
                print(f"   Session Active: {is_active}")
                print(f"   Agent Online: {agent_status['active']}")
                print(f"   Disconnect Reason: {agent_status['reason']}")
                break
            
            print("---")
            time.sleep(3)
            
    except KeyboardInterrupt:
        print("\n⏹️ Monitoring stopped by user")

if __name__ == "__main__":
    test_agent_disconnect_detection()