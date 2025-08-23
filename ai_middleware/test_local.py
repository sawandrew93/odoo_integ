#!/usr/bin/env python3
import requests
import json

# Test the API locally
def test_chat():
    url = "http://localhost:8000/chat"
    data = {
        "message": "What are your business hours?",
        "visitor_name": "Test User"
    }
    
    try:
        response = requests.post(url, json=data)
        print("Status:", response.status_code)
        print("Response:", json.dumps(response.json(), indent=2))
    except Exception as e:
        print("Error:", e)

def test_health():
    try:
        response = requests.get("http://localhost:8000/health")
        print("Health check:", response.json())
    except Exception as e:
        print("Health check failed:", e)

if __name__ == "__main__":
    test_health()
    test_chat()