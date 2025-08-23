#!/usr/bin/env python3
import uvicorn
from src.main import app

if __name__ == "__main__":
    print("Starting AI Middleware server...")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)