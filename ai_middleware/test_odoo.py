#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from src.odoo_client import OdooClient

load_dotenv()

def test_odoo_connection():
    client = OdooClient(
        url=os.getenv('ODOO_URL'),
        db=os.getenv('ODOO_DB'), 
        username=os.getenv('ODOO_USERNAME'),
        password=os.getenv('ODOO_PASSWORD')
    )
    
    print("Testing Odoo connection...")
    print(f"URL: {client.url}")
    print(f"DB: {client.db}")
    print(f"Username: {client.username}")
    
    # Test authentication
    if client.authenticate():
        print(f"✅ Authentication successful! UID: {client.uid}")
        
        # Test creating live chat session
        session_id = client.create_live_chat_session("Test User", "Hello from API test")
        if session_id:
            print(f"✅ Live chat session created! ID: {session_id}")
        else:
            print("❌ Failed to create live chat session")
    else:
        print("❌ Authentication failed")

if __name__ == "__main__":
    test_odoo_connection()