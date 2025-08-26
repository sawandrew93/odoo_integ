(function() {
    'use strict';

    class ChatWidget {
        constructor(options = {}) {
            this.options = {
                serverUrl: 'https://odoo.andrewdemo.online',
                position: 'bottom-right',
                primaryColor: '#007bff',
                title: 'Get support from our AI assistant or connect with a representative.',
                ...options
            };

            this.sessionId = null;
            this.websocket = null;
            this.isOpen = false;
            this.sessionEnded = false;
            this.isConnectedToHuman = false;
            this.reconnectAttempts = 0;
            this.maxReconnectAttempts = 5;

            this.init();
        }

        init() {
            this.createWidget();
            this.addMessage("Hello! How can I help you today?", 'bot');
        }

        createWidget() {
            this.widget = document.createElement('div');
            this.widget.id = 'chat-widget';
            this.widget.innerHTML = this.getWidgetHTML();
            document.body.appendChild(this.widget);

            const style = document.createElement('style');
            style.textContent = this.getWidgetCSS();
            document.head.appendChild(style);

            this.addEventListeners();
        }

        getWidgetHTML() {
            return `
                <div class="chat-widget-container ${this.options.position}">
                    <div class="chat-toggle" id="chat-toggle">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                        </svg>
                    </div>

                    <div class="chat-window" id="chat-window" style="display: none;">
                        <div class="chat-header">
                            <span class="chat-title">${this.options.title}</span>
                            <div class="connection-status" id="connection-status">
                                <span class="status-text">AI Assistant</span>
                                <div class="status-indicator"></div>
                            </div>
                        </div>

                        <div class="chat-messages" id="chat-messages"></div>

                        <div class="chat-input-container" id="chat-input-container">
                            <div class="input-group">
                                <input type="text" id="chat-input" placeholder="Type your message..." />
                                <button id="chat-send">Send</button>
                                <button id="request-human" title="Connect with human support">👤</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }

        getWidgetCSS() {
            return `
                .chat-widget-container {
                    position: fixed;
                    z-index: 10000;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }

                .chat-widget-container.bottom-right {
                    bottom: 20px;
                    right: 20px;
                }

                .chat-toggle {
                    width: 60px;
                    height: 60px;
                    background: ${this.options.primaryColor};
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                    transition: all 0.3s ease;
                    color: white;
                }

                .chat-toggle:hover {
                    transform: scale(1.1);
                }

                .chat-window {
                    width: 350px;
                    height: 500px;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                    display: flex;
                    flex-direction: column;
                    position: absolute;
                    bottom: 70px;
                    right: 0;
                }

                .chat-header {
                    background: ${this.options.primaryColor};
                    color: white;
                    padding: 16px;
                    border-radius: 12px 12px 0 0;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }

                .chat-title {
                    font-weight: 600;
                    flex: 1;
                    font-size: 14px;
                }

                .connection-status {
                    display: flex;
                    align-items: center;
                    gap: 6px;
                }

                .status-text {
                    font-size: 11px;
                    opacity: 0.9;
                }

                .status-indicator {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: #4CAF50;
                }

                .status-indicator.waiting {
                    background: #FFC107;
                    animation: pulse 1.5s infinite;
                }

                .status-indicator.human {
                    background: #4CAF50;
                }

                @keyframes pulse {
                    0% { opacity: 1; }
                    50% { opacity: 0.5; }
                    100% { opacity: 1; }
                }

                .chat-messages {
                    flex: 1;
                    overflow-y: auto;
                    padding: 16px;
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                }

                .message {
                    display: flex;
                    margin-bottom: 8px;
                }

                .message-content {
                    max-width: 80%;
                    padding: 12px 16px;
                    border-radius: 18px;
                    word-wrap: break-word;
                    font-size: 14px;
                    line-height: 1.4;
                }

                .bot-message .message-content,
                .agent-message .message-content {
                    background: #f1f1f1;
                    color: #333;
                    margin-right: auto;
                }

                .system-message .message-content {
                    background: #e3f2fd;
                    color: #1976d2;
                    margin-right: auto;
                    font-style: italic;
                    font-size: 13px;
                    text-align: center;
                    max-width: 90%;
                }

                .user-message {
                    justify-content: flex-end;
                }

                .user-message .message-content {
                    background: ${this.options.primaryColor};
                    color: white;
                    margin-left: auto;
                }

                .chat-input-container {
                    padding: 16px;
                    border-top: 1px solid #eee;
                }

                .input-group {
                    display: flex;
                    gap: 8px;
                }

                #chat-input {
                    flex: 1;
                    padding: 12px;
                    border: 1px solid #ddd;
                    border-radius: 20px;
                    outline: none;
                    font-size: 14px;
                }

                #chat-send {
                    padding: 12px 16px;
                    background: ${this.options.primaryColor};
                    color: white;
                    border: none;
                    border-radius: 20px;
                    cursor: pointer;
                    font-size: 14px;
                    transition: all 0.3s ease;
                }

                #request-human {
                    background: #28a745;
                    color: white;
                    padding: 12px;
                    border: none;
                    border-radius: 50%;
                    cursor: pointer;
                    font-size: 16px;
                    width: 44px;
                    height: 44px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                #chat-send:hover, #request-human:hover {
                    transform: translateY(-1px);
                    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                }

                .typing-indicator {
                    display: flex;
                    align-items: center;
                    gap: 4px;
                    padding: 12px 16px;
                    background: #f1f1f1;
                    border-radius: 18px;
                    margin-right: auto;
                    max-width: 80px;
                }

                .typing-dot {
                    width: 8px;
                    height: 8px;
                    background: #999;
                    border-radius: 50%;
                    animation: typing 1.4s infinite ease-in-out;
                }

                .typing-dot:nth-child(1) { animation-delay: -0.32s; }
                .typing-dot:nth-child(2) { animation-delay: -0.16s; }

                @keyframes typing {
                    0%, 80%, 100% { transform: scale(0); }
                    40% { transform: scale(1); }
                }

                @media (max-width: 480px) {
                    .chat-window {
                        width: calc(100vw - 40px);
                        height: calc(100vh - 100px);
                        bottom: 70px;
                        right: 20px;
                    }
                }
            `;
        }

        addEventListeners() {
            const toggle = document.getElementById('chat-toggle');
            const input = document.getElementById('chat-input');
            const send = document.getElementById('chat-send');
            const requestHuman = document.getElementById('request-human');

            toggle.addEventListener('click', () => this.toggleChat());
            send.addEventListener('click', () => this.sendMessage());
            requestHuman.addEventListener('click', () => this.requestHuman());

            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.sendMessage();
                }
            });
        }

        toggleChat() {
            const window = document.getElementById('chat-window');
            this.isOpen = !this.isOpen;
            window.style.display = this.isOpen ? 'flex' : 'none';
        }

        connectWebSocket() {
            if (!this.sessionId) return;
            
            this.websocket = new WebSocket(`wss://odoo.andrewdemo.online/ws/${this.sessionId}`);
            
            this.websocket.onopen = () => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
                this.updateConnectionStatus('Connected', this.isConnectedToHuman ? 'Human Agent' : 'AI Assistant');
            };
            
            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleServerMessage(data);
            };
            
            this.websocket.onclose = () => {
                console.log('WebSocket disconnected');
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    setTimeout(() => this.connectWebSocket(), 2000);
                }
            };
        }

        handleServerMessage(data) {
            switch (data.type) {
                case 'message':
                    this.hideTypingIndicator();
                    this.addMessage(`${data.data.author}: ${data.data.body}`, 'agent');
                    break;
                case 'agent_joined':
                    this.isConnectedToHuman = true;
                    this.updateConnectionStatus('Human Agent', 'Connected to agent');
                    this.addMessage('Agent joined the chat', 'system');
                    document.getElementById('request-human').disabled = true;
                    break;
                case 'session_ended':
                    this.addMessage(data.message, 'system');
                    this.sessionEnded = true;
                    document.getElementById('chat-input').disabled = true;
                    document.getElementById('chat-send').disabled = true;
                    break;
            }
        }

        updateConnectionStatus(statusText, tooltip, isWaiting = false) {
            const statusElement = document.getElementById('connection-status');
            let indicatorClass = '';

            if (isWaiting) {
                indicatorClass = 'waiting';
            } else if (this.isConnectedToHuman) {
                indicatorClass = 'human';
            }

            statusElement.innerHTML = `
                <span class="status-text" title="${tooltip}">${statusText}</span>
                <div class="status-indicator ${indicatorClass}"></div>
            `;
        }

        async sendMessage() {
            const input = document.getElementById('chat-input');
            const message = input.value.trim();

            if (!message || this.sessionEnded) return;

            this.addMessage(message, 'user');
            input.value = '';

            if (!this.isConnectedToHuman) {
                this.showTypingIndicator();
            }

            try {
                const response = await fetch(`${this.options.serverUrl}/chat`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        message: message,
                        visitor_name: 'Website Visitor',
                        session_id: this.sessionId ? this.sessionId.toString() : null
                    })
                });

                const data = await response.json();
                
                if (data.handoff_needed && data.odoo_session_id && !this.sessionId) {
                    this.sessionId = data.odoo_session_id;
                    this.hideTypingIndicator();
                    this.addMessage(data.response, 'system');
                    this.connectWebSocket();
                } else if (data.response) {
                    this.hideTypingIndicator();
                    this.addMessage(data.response, 'bot');
                }
            } catch (error) {
                this.hideTypingIndicator();
                this.addMessage('Sorry, there was an error. Please try again.', 'system');
            }
        }

        requestHuman() {
            this.addMessage('Requesting human agent...', 'system');
            // This will be handled by the AI when it detects the request
        }

        addMessage(message, sender) {
            const messagesContainer = document.getElementById('chat-messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}-message`;

            messageDiv.innerHTML = `
                <div class="message-content">${message}</div>
            `;

            messagesContainer.appendChild(messageDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        showTypingIndicator() {
            this.hideTypingIndicator();

            const messagesContainer = document.getElementById('chat-messages');
            const typingDiv = document.createElement('div');
            typingDiv.className = 'message bot-message';
            typingDiv.id = 'typing-indicator';

            typingDiv.innerHTML = `
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            `;

            messagesContainer.appendChild(typingDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        hideTypingIndicator() {
            const typingIndicator = document.getElementById('typing-indicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }
        }
    }

    // Initialize the chat widget
    window.ChatWidget = ChatWidget;
    window.chatWidget = new ChatWidget({
        serverUrl: 'https://odoo.andrewdemo.online',
        position: 'bottom-right',
        primaryColor: '#007bff',
        title: 'Get support from our AI assistant or connect with a representative.'
    });
})();