(function() {
    const CONFIG = {
        API_BASE: 'https://odoo.andrewdemo.online',
        WS_BASE: 'wss://odoo.andrewdemo.online'
    };

    let sessionId = null;
    let websocket = null;
    let sessionEnded = false;
    let isMinimized = true; // Start minimized

    function createWidget() {
        const widget = document.createElement('div');
        widget.id = 'ai-chat-widget';
        widget.innerHTML = `
            <div id="chat-container" style="position:fixed;bottom:20px;right:20px;width:60px;height:60px;border:none;border-radius:50%;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);box-shadow:0 4px 12px rgba(0,0,0,0.3);display:flex;flex-direction:column;z-index:9999;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;transition:all 0.3s ease;overflow:hidden;">
                <div id="chat-header" style="padding:0;background:transparent;color:white;font-weight:600;cursor:pointer;display:flex;justify-content:center;align-items:center;flex-shrink:0;width:100%;height:100%;">
                    <span style="font-size:24px;">💬</span>
                </div>
                <div id="chat-body" style="flex:1;display:none;flex-direction:column;background:white;min-height:0;">
                    <div id="chat-messages" style="flex:1;padding:20px;overflow-y:auto;background:linear-gradient(to bottom,#f8f9fa,#ffffff);min-height:0;"></div>
                    <div style="padding:16px 20px;background:white;border-top:1px solid #e9ecef;flex-shrink:0;">
                        <div style="display:flex;gap:8px;">
                            <input type="text" id="message-input" placeholder="Type your message..." style="flex:1;padding:12px 16px;border:2px solid #e9ecef;border-radius:25px;outline:none;font-size:14px;transition:border-color 0.2s ease;">
                            <button id="send-btn" style="padding:12px 20px;background:linear-gradient(135deg,#667eea,#764ba2);color:white;border:none;border-radius:25px;cursor:pointer;font-weight:600;transition:transform 0.2s ease;min-width:60px;">Send</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(widget);
        return widget;
    }

    function addMessage(content, isUser = false, isSystem = false) {
        const messagesDiv = document.getElementById('chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.style.cssText = `margin:8px 0;padding:12px 16px;border-radius:18px;max-width:80%;word-wrap:break-word;font-size:14px;line-height:1.4;${
            isUser ? 'background:linear-gradient(135deg,#667eea,#764ba2);color:white;margin-left:auto;text-align:right;' : 
            isSystem ? 'background:#e8f5e8;font-style:italic;text-align:center;color:#666;margin:0 auto;' :
            'background:#f1f3f4;color:#333;margin-right:auto;'
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
            } else if (data.type === 'agent_joined') {
                addMessage(data.message, false, true);
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

    function toggleMinimize() {
        const container = document.getElementById('chat-container');
        const chatBody = document.getElementById('chat-body');
        
        if (isMinimized) {
            // Maximize - responsive sizing
            const isMobile = window.innerWidth <= 480;
            container.style.width = isMobile ? 'calc(100vw - 40px)' : '350px';
            container.style.height = isMobile ? 'calc(100vh - 40px)' : '500px';
            container.style.borderRadius = '16px';
            container.style.bottom = '20px';
            container.style.right = '20px';
            if (isMobile) container.style.left = '20px';
            container.classList.add('maximized');
            chatBody.style.display = 'flex';
            document.querySelector('#chat-header span').textContent = '💬 Ask Vanguard';
            document.querySelector('#chat-header span').style.fontSize = '16px';
            document.querySelector('#chat-header').style.padding = '16px 20px';
            document.querySelector('#chat-header').style.background = 'rgba(255,255,255,0.1)';
            document.querySelector('#chat-header').style.borderBottom = '1px solid rgba(255,255,255,0.1)';
            document.querySelector('#chat-header').style.height = '60px';
            isMinimized = false;
        } else {
            // Minimize - fixed small circle
            container.style.width = '60px';
            container.style.height = '60px';
            container.style.borderRadius = '50%';
            container.style.bottom = '20px';
            container.style.right = '20px';
            container.style.left = 'auto';
            container.classList.remove('maximized');
            chatBody.style.display = 'none';
            document.querySelector('#chat-header span').textContent = '💬';
            document.querySelector('#chat-header span').style.fontSize = '24px';
            document.querySelector('#chat-header').style.padding = '0';
            document.querySelector('#chat-header').style.background = 'transparent';
            document.querySelector('#chat-header').style.borderBottom = 'none';
            document.querySelector('#chat-header').style.height = '100%';
            isMinimized = true;
        }
    }

    // Add CSS styles
    const style = document.createElement('style');
    style.textContent = `
        #message-input:focus { border-color: #667eea !important; }
        #send-btn:hover { transform: scale(1.05) !important; }
        #chat-header:hover { background: rgba(255,255,255,0.15) !important; }
        #chat-header { cursor: pointer !important; user-select: none !important; -webkit-user-select: none !important; -moz-user-select: none !important; -ms-user-select: none !important; }
        #chat-messages::-webkit-scrollbar { width: 4px; }
        #chat-messages::-webkit-scrollbar-track { background: #f1f1f1; }
        #chat-messages::-webkit-scrollbar-thumb { background: #c1c1c1; border-radius: 2px; }
        @media (max-width: 480px) {
            #chat-container.maximized { width: calc(100vw - 40px) !important; height: calc(100vh - 40px) !important; bottom: 20px !important; right: 20px !important; left: 20px !important; }
        }
    `;
    document.head.appendChild(style);

    // Initialize widget
    const widget = createWidget();
    addMessage('Hello! How can I help you today?');
    


    document.getElementById('send-btn').onclick = sendMessage;
    document.getElementById('message-input').onkeypress = (e) => {
        if (e.key === 'Enter') sendMessage();
    };
    document.getElementById('chat-header').onclick = toggleMinimize;
})();