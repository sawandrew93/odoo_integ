# WebSocket Implementation Guide

This project now supports both **WebSocket** and **Polling** modes for real-time communication.

## 🚀 Quick Start

1. **Install new dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the server:**
   ```bash
   python run.py
   ```

3. **Test WebSocket support:**
   ```bash
   python test_websocket.py
   ```

4. **Use the enhanced widget:**
   Open `widget_websocket.html` in your browser

## 📊 Performance Comparison

Run the performance comparison:
```bash
python compare_modes.py
```

This will show you latency differences between WebSocket and polling modes.

## 🔧 How It Works

### WebSocket Mode (Preferred)
- **Real-time**: Instant message delivery
- **Efficient**: Lower server load, less battery usage
- **Automatic fallback**: Falls back to polling if WebSocket fails

### Polling Mode (Fallback)
- **Compatible**: Works with all Odoo Online instances
- **Reliable**: Handles network issues gracefully
- **3-second intervals**: Checks for new messages every 3 seconds

## 🌐 Widget Features

The new `widget_websocket.html` includes:

- **Automatic detection**: Tries WebSocket first, falls back to polling
- **Connection status**: Shows current connection mode
- **Reconnection logic**: Automatically reconnects on failures
- **Keep-alive**: Ping/pong to maintain WebSocket connections

### Connection Status Indicators:
- 🟢 **Real-time connected**: WebSocket active
- 🟡 **Using polling mode**: Fallback active  
- 🔴 **Connection error**: Attempting reconnection

## 🔍 Testing Your Setup

### Basic Test
```bash
python test_websocket.py
```

### Performance Test
```bash
python compare_modes.py
```

### Manual Test
1. Open `widget_websocket.html`
2. Send a message that triggers agent handoff
3. Watch the connection status indicator
4. Check browser console for WebSocket logs

## 🛠️ Troubleshooting

### WebSocket Not Working?
This is normal for some Odoo Online instances. The widget automatically falls back to polling.

### High Latency?
Run `compare_modes.py` to see if polling might be more reliable for your setup.

### Connection Drops?
The widget includes automatic reconnection with exponential backoff.

## 📁 File Structure

```
ai_middleware/
├── widget_websocket.html     # Enhanced widget with WebSocket support
├── widget_integration.html   # Original polling-only widget
├── test_websocket.py        # WebSocket functionality tests
├── compare_modes.py         # Performance comparison tool
└── src/
    └── main.py              # Updated with WebSocket endpoints
```

## 🔧 Configuration

The WebSocket implementation uses these settings:

- **Ping interval**: 30 seconds (keep-alive)
- **Reconnection attempts**: 3 maximum
- **Polling fallback**: 3-second intervals
- **Connection timeout**: 5 seconds

## 💡 Best Practices

1. **Always use `widget_websocket.html`** - it automatically chooses the best mode
2. **Monitor connection status** - the widget shows current mode
3. **Test your specific Odoo instance** - WebSocket support varies
4. **Keep the original widget** as backup if needed

## 🚨 Odoo Online Compatibility

WebSocket support depends on your Odoo Online configuration:
- ✅ **Most instances**: Support WebSocket connections
- ⚠️ **Some instances**: May block WebSocket due to proxy/firewall
- 🔄 **Automatic fallback**: System detects and switches to polling

The implementation is designed to work regardless of your Odoo Online setup.