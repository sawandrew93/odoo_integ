# AI Agent Middleware for Odoo Live Chat

This project implements an AI middleware that sits between your website chat widget and Odoo Online Live Chat, providing intelligent routing and automated responses.

## Architecture

```
Customer → Chat Widget → AI Middleware → Decision Engine
                                      ↓
                              AI Response OR Odoo Handoff
```

## Setup

1. **Install Dependencies**
   ```bash
   cd ai_middleware
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Add Knowledge Base**
   - Place your FAQ/knowledge documents as .txt files in `knowledge/` directory
   - The AI will use these for context when answering questions

4. **Run the Server**
   ```bash
   python run.py
   ```

## Configuration

Edit `.env` file:
- `ODOO_URL`: Your Odoo instance URL
- `ODOO_DB`: Database name
- `ODOO_USERNAME`: Odoo username
- `ODOO_PASSWORD`: Odoo password  
- `OPENAI_API_KEY`: OpenAI API key
- `CONFIDENCE_THRESHOLD`: AI confidence threshold (0.0-1.0)

## API Endpoints

### POST /chat
Handle chat messages and determine AI response or handoff.

**Request:**
```json
{
  "message": "How do I reset my password?",
  "visitor_name": "John Doe",
  "context": "User is on login page"
}
```

**Response:**
```json
{
  "response": "Click on 'Forgot Password' on the login page...",
  "handoff_needed": false,
  "confidence": 0.85,
  "odoo_session_id": null
}
```

## Integration

Replace your current chat widget endpoint with:
```javascript
fetch('http://localhost:8000/chat', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    message: userMessage,
    visitor_name: visitorName
  })
})
```

## Testing

Open `widget_integration.html` in your browser to test the chat flow.

## Deployment

For production:
1. Use environment variables for secrets
2. Deploy with gunicorn: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.main:app`
3. Set up reverse proxy (nginx)
4. Enable HTTPS