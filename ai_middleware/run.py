import uvicorn

if __name__ == "__main__":
    # Run with WebSocket support
    uvicorn.run(
        "src.main:app", 
        host="0.0.0.0", 
        port=8080, 
        reload=True,
        ws_ping_interval=20,
        ws_ping_timeout=10
    )