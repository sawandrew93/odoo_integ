(function() {
    const CONFIG = {
        API_BASE: 'https://odoo.andrewdemo.online',
        WS_BASE: 'wss://odoo.andrewdemo.online'
    };

    let sessionId = null;
    let websocket = null;
    let sessionEnded = false;

    function createWidget() {
        const widget = document.createElement('div');
        widget.id = 'ai-chat-widget';
        widget.innerHTML = `
            <div style="position:fixed;bottom:20px;right:20px;width:300px;height:400px;border:1px solid #ccc;border-radius:10px;background:white;box-shadow:0 4px 12px rgba(0,0,0,0.15);display:flex;flex-direction:column;z-index:9999;font-family:Arial,sans-serif;">
                <div style="padding:10px;background:#007bff;color:white;border-radius:10px 10px 0 0;font-weight:bold;">Ask Vanguard</div>
                <div id="chat-messages" style="flex:1;padding:10px;overflow-y:auto;border-bottom:1px solid #eee;"></div>
                <div style="display:flex;padding:10px;">
                    <input type="text" id="message-input" placeholder="Type your message..." style="flex:1;padding:8px;border:1px solid #ddd;border-radius:4px;margin-right:8px;">
                    <button id="send-btn" style="padding:8px 16px;background:#007bff;color:white;border:none;border-radius:4px;cursor:pointer;">Send</button>
                </div>
            </div>
        `;
        document.body.appendChild(widget);
        return widget;
    }

    function addMessage(content, isUser = false, isSystem = false) {
        const messagesDiv = document.getElementById('chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.style.cssText = `margin:5px 0;padding:8px;border-radius:8px;${
            isUser ? 'background:#e3f2fd;text-align:right;' : 
            isSystem ? 'background:#e8f5e8;font-style:italic;text-align:center;color:#666;' :
            'background:#f5f5f5;'
        }`;
        messageDiv.textContent = content;
        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    function connectWebSocket() {
        if (!sessionId) return;
        
        websocket = new WebSocket(`${CONFIG.WS_BASE}/ws/${sessionId}`);
        
        websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'message') {
                addMessage(`${data.data.author}: ${data.data.body}`);
            } else if (data.type === 'session_ended') {
                addMessage(data.message, false, true);
                sessionEnded = true;
                document.getElementById('message-input').disabled = true;
                document.getElementById('send-btn').disabled = true;
            }
        };
    }

    async function sendMessage() {
        const input = document.getElementById('message-input');
        const message = input.value.trim();
        if (!message || sessionEnded) return;

        addMessage(message, true);
        input.value = '';

        try {
            const response = await fetch(`${CONFIG.API_BASE}/chat`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    message: message,
                    visitor_name: 'Website Visitor',
                    session_id: sessionId ? sessionId.toString() : null
                })
            });

            const data = await response.json();
            
            if (data.handoff_needed && data.odoo_session_id && !sessionId) {
                sessionId = data.odoo_session_id;
                addMessage(data.response);
                connectWebSocket();
            } else if (data.response) {
                addMessage(data.response);
            }
        } catch (error) {
            addMessage('Sorry, there was an error. Please try again.');
        }
    }

    // Initialize widget
    const widget = createWidget();
    addMessage('Hello! How can I help you today?');
    
    document.getElementById('send-btn').onclick = sendMessage;
    document.getElementById('message-input').onkeypress = (e) => {
        if (e.key === 'Enter') sendMessage();
    };
})();