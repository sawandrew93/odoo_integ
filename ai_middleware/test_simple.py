#!/usr/bin/env python3
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def test_chat_flow():
    API_BASE = 'http://localhost:8000'
    
    print("Testing chat flow...")
    
    # Test 1: Initial message (should trigger handoff)
    print("\n1. Sending initial message...")
    response = requests.post(f'{API_BASE}/chat', json={
        'message': 'I need help with my account',
        'visitor_name': 'Test User'
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {data}")
        
        if data.get('handoff_needed') and data.get('odoo_session_id'):
            session_id = data['odoo_session_id']
            print(f"✅ Session created: {session_id}")
            
            # Test 2: Send follow-up message
            print("\n2. Sending follow-up message...")
            response2 = requests.post(f'{API_BASE}/chat', json={
                'message': 'Are you there?',
                'visitor_name': 'Test User',
                'session_id': str(session_id)
            })
            
            if response2.status_code == 200:
                data2 = response2.json()
                print(f"Follow-up response: {data2}")
                
                # Test 3: Check session status
                print("\n3. Checking session status...")
                status_response = requests.get(f'{API_BASE}/session/{session_id}/status')
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"Session status: {status_data}")
                
                # Test 4: Get messages
                print("\n4. Getting messages...")
                msg_response = requests.get(f'{API_BASE}/messages/{session_id}')
                if msg_response.status_code == 200:
                    msg_data = msg_response.json()
                    print(f"Messages: {msg_data}")
            else:
                print(f"❌ Follow-up failed: {response2.status_code}")
        else:
            print("❌ No handoff triggered")
    else:
        print(f"❌ Initial request failed: {response.status_code}")

if __name__ == "__main__":
    test_chat_flow()