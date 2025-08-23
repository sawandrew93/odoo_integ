#!/usr/bin/env python3
import os
import time
from dotenv import load_dotenv
from src.odoo_client import OdooClient

load_dotenv()

def test_new_session():
    client = OdooClient(
        url=os.getenv('ODOO_URL'),
        db=os.getenv('ODOO_DB'), 
        username=os.getenv('ODOO_USERNAME'),
        password=os.getenv('ODOO_PASSWORD')
    )
    
    if not client.authenticate():
        print("❌ Auth failed")
        return
    
    # Create new session
    session_id = client.create_live_chat_session("Test User", "Hello, I need help")
    if not session_id:
        print("❌ Failed to create session")
        return
    
    print(f"✅ Created session {session_id}")
    print("Now join as agent in Odoo, then leave...")
    
    last_operator = None
    
    try:
        while True:
            # Get messages (this will detect operator changes)
            messages = client.get_session_messages(session_id)
            
            # Check current operator
            session_data = {
                "jsonrpc": "2.0",
                "method": "call", 
                "params": {
                    "model": "discuss.channel",
                    "method": "read",
                    "args": [[session_id], ["livechat_operator_id"]],
                    "kwargs": {}
                },
                "id": 1
            }
            
            response = client.session.post(f"{client.url}/web/dataset/call_kw", json=session_data)
            if response.status_code == 200:
                result = response.json()
                if result.get('result'):
                    current_operator = result['result'][0].get('livechat_operator_id')
                    
                    if current_operator != last_operator:
                        print(f"Operator changed: {last_operator} -> {current_operator}")
                        last_operator = current_operator
            
            # Check for disconnect messages
            for msg in messages:
                if msg['body'] in ['SESSION_ENDED', 'AGENT_DISCONNECTED']:
                    print(f"🚨 DETECTED: {msg['body']}")
                    return
            
            print(f"Messages: {len(messages)}, Operator: {last_operator}")
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nStopped")

if __name__ == "__main__":
    test_new_session()