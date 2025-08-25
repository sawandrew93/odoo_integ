# AI Agent Middleware for Odoo Live Chat

Real-time AI middleware that sits between your website chat widget and Odoo Online Live Chat, providing intelligent routing and automated responses with WebSocket support.

## Features

- ✅ **Real-time WebSocket communication** for instant visitor experience
- ✅ **AI-powered message routing** with Google Gemini integration
- ✅ **Seamless Odoo integration** with instant agent notifications
- ✅ **Automatic feedback collection** after chat sessions
- ✅ **Agent join/leave notifications** for better user experience
- ✅ **Knowledge base integration** for contextual AI responses

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Odoo and Gemini credentials
   ```

3. **Add Knowledge Base**
   - Place FAQ/knowledge documents as .txt files in `knowledge/` directory

4. **Run the Server**
   ```bash
   python run.py
   ```

5. **Use the Chat Widget**
   - Open `widget_websocket_fixed.html` in your browser
   - Test the real-time chat functionality

## Configuration

Edit `.env` file with your credentials:
```
ODOO_URL=https://your-instance.odoo.com
ODOO_DB=your-database-name
ODOO_USERNAME=your-username
ODOO_PASSWORD=your-password
GEMINI_API_KEY=your-gemini-api-key
CONFIDENCE_THRESHOLD=0.7
```

## API Endpoints

- `POST /chat` - Handle chat messages and AI routing
- `GET /session/{session_id}/status` - Check session status
- `POST /feedback` - Submit chat feedback
- `WS /ws/{session_id}` - WebSocket for real-time updates
- `GET /health` - Health check
- `GET /connections` - Active WebSocket connections

## Architecture

```
Visitor → Chat Widget → AI Middleware → Decision Engine
                            ↓              ↓
                    WebSocket Updates   Odoo Live Chat
                            ↓              ↓
                    Real-time Response  Agent Notification
```

## Real-time Flow

1. **Visitor sends message** → Instant delivery to Odoo + agent notification ⚡
2. **AI processes message** → Instant response or handoff decision ⚡
3. **Agent joins chat** → Instant notification to visitor ⚡
4. **Agent replies** → 1-second detection + instant WebSocket delivery ⚡
5. **Session ends** → Automatic feedback survey ⚡

## Project Structure

```
ai_middleware/
├── src/
│   ├── main.py              # FastAPI application
│   ├── odoo_client.py       # Odoo API integration
│   ├── ai_agent.py          # Google Gemini integration
│   ├── knowledge_base.py    # FAQ/knowledge management
│   └── websocket_manager.py # Real-time WebSocket handling
├── knowledge/
│   └── sample_faq.txt       # Knowledge base files
├── widget_websocket_fixed.html # Chat widget with WebSocket
├── requirements.txt         # Python dependencies
├── run.py                  # Server startup script
└── .env.example            # Environment configuration template
```

## Deployment

For production deployment:

1. **Use environment variables** for all secrets
2. **Deploy with gunicorn**:
   ```bash
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.main:app
   ```
3. **Set up reverse proxy** (nginx) for HTTPS
4. **Configure CORS** for your domain
5. **Monitor WebSocket connections** via `/connections` endpoint

## Integration

Replace your current chat widget endpoint:
```javascript
// Use the provided widget_websocket_fixed.html
// Or integrate the WebSocket connection in your existing widget
const ws = new WebSocket(`ws://your-server:8000/ws/${sessionId}`);
```

## Performance

- **WebSocket latency**: ~50ms for real-time updates
- **Agent notification**: Instant via Odoo bus system
- **AI response time**: ~500ms with Google Gemini
- **Polling fallback**: 1-second interval for agent messages
- **Session monitoring**: 30-second health checks

## Support

This middleware provides a production-ready solution for real-time AI-powered chat with Odoo Online integration using Google Gemini 2.0 Flash and text-embedding-001.