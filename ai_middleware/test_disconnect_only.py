#!/usr/bin/env python3
import os
import time
from dotenv import load_dotenv
from src.odoo_client import OdooClient

load_dotenv()

def monitor_session_disconnect():
    client = OdooClient(
        url=os.getenv('ODOO_URL'),
        db=os.getenv('ODOO_DB'), 
        username=os.getenv('ODOO_USERNAME'),
        password=os.getenv('ODOO_PASSWORD')
    )
    
    if not client.authenticate():
        print("❌ Auth failed")
        return
    
    # Use existing session ID or create new one
    session_id = 76  # Replace with actual session ID
    
    print(f"Monitoring session {session_id} for agent disconnect...")
    print("Join as agent in Odoo, then leave the session")
    
    last_operator_status = None
    
    try:
        while True:
            # Check operator status
            session_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "discuss.channel",
                    "method": "read",
                    "args": [[session_id], ["livechat_operator_id", "livechat_status", "livechat_end_dt"]],
                    "kwargs": {}
                },
                "id": 1
            }
            
            response = client.session.post(f"{client.url}/web/dataset/call_kw", json=session_data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('result') and len(result['result']) > 0:
                    data = result['result'][0]
                    operator_id = data.get('livechat_operator_id')
                    status = data.get('livechat_status')
                    end_dt = data.get('livechat_end_dt')
                    
                    current_status = bool(operator_id)
                    
                    print(f"Operator: {operator_id}, Status: {status}, End: {end_dt}")
                    
                    # Detect when operator changes from present to absent
                    if last_operator_status is True and current_status is False:
                        print("🚨 AGENT LEFT DETECTED! Operator removed from session")
                        break
                    
                    if status in ['closed', 'ended'] or end_dt:
                        print("🚨 SESSION ENDED DETECTED!")
                        break
                    
                    last_operator_status = current_status
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nStopped monitoring")

if __name__ == "__main__":
    monitor_session_disconnect()