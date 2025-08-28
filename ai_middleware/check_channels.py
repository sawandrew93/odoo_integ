#!/usr/bin/env python3
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv('.env')

ODOO_URL = os.getenv('ODOO_URL')
ODOO_DB = os.getenv('ODOO_DB') 
ODOO_USERNAME = os.getenv('ODOO_USERNAME')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD')

def authenticate():
    session = requests.Session()
    session.headers.update({
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (compatible; Channel-Checker/1.0)'
    })
    
    auth_data = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": ODOO_DB,
            "login": ODOO_USERNAME,
            "password": ODOO_PASSWORD
        },
        "id": 1
    }
    
    response = session.post(f"{ODOO_URL}/web/session/authenticate", json=auth_data)
    result = response.json()
    
    if result.get('result') and result['result'].get('uid'):
        print(f"✅ Authentication successful - UID: {result['result']['uid']}")
        return session, result['result']['uid']
    else:
        print(f"❌ Authentication failed: {result}")
        return None, None

def get_live_chat_channels(session):
    channel_data = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": "im_livechat.channel",
            "method": "search_read",
            "args": [[], ["id", "name", "user_ids", "are_you_inside"]],
            "kwargs": {}
        },
        "id": 2
    }
    
    response = session.post(f"{ODOO_URL}/web/dataset/call_kw", json=channel_data)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('result'):
            return result['result']
    
    return []

def check_channel_availability(session, channel_id):
    rpc_data = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "channel_id": channel_id,
            "anonymous_name": "Test Visitor",
            "previous_operator_id": False,
            "country_id": False,
            "user_id": False,
            "persisted": False
        },
        "id": 3
    }
    
    response = session.post(f"{ODOO_URL}/im_livechat/get_session", json=rpc_data)
    
    if response.status_code == 200:
        result = response.json()
        return result.get('result', False) != False
    
    return False

def main():
    print(f"🔍 Checking live chat channels for: {ODOO_URL}")
    print(f"Database: {ODOO_DB}")
    print(f"Username: {ODOO_USERNAME}")
    print("-" * 50)
    
    session, uid = authenticate()
    if not session:
        return
    
    channels = get_live_chat_channels(session)
    
    if not channels:
        print("❌ No live chat channels found!")
        return
    
    print(f"📋 Found {len(channels)} live chat channel(s):")
    print()
    
    for channel in channels:
        print(f"Channel ID: {channel['id']}")
        print(f"Name: {channel['name']}")
        print(f"Operators: {len(channel.get('user_ids', []))}")
        print(f"Are you inside: {channel.get('are_you_inside', False)}")
        
        available = check_channel_availability(session, channel['id'])
        status = "🟢 AVAILABLE" if available else "🔴 OFFLINE/UNAVAILABLE"
        print(f"Status: {status}")
        print("-" * 30)

if __name__ == "__main__":
    main()