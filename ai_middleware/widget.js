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

    function addMessage(content, isUser = false, isSystem = false, attachments = []) {
        const messagesDiv = document.getElementById('chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.style.cssText = `margin:8px 0;padding:12px 16px;border-radius:18px;max-width:80%;word-wrap:break-word;font-size:14px;line-height:1.4;${
            isUser ? 'background:linear-gradient(135deg,#667eea,#764ba2);color:white;margin-left:auto;text-align:right;' : 
            isSystem ? 'background:#e8f5e8;font-style:italic;text-align:center;color:#666;margin:0 auto;' :
            'background:#f1f3f4;color:#333;margin-right:auto;'
        }`;
        
        // Add text content
        if (content) {
            const textDiv = document.createElement('div');
            textDiv.textContent = content;
            messageDiv.appendChild(textDiv);
        }
        
        // Add attachments if any
        if (attachments && attachments.length > 0) {
            const attachmentsDiv = document.createElement('div');
            attachmentsDiv.style.cssText = 'margin-top:8px;';
            
            attachments.forEach(attachment => {
                // Handle different media types
                if (attachment.mimetype.startsWith('image/')) {
                    const imgDiv = document.createElement('div');
                    imgDiv.style.cssText = 'margin:4px 0;';
                    imgDiv.innerHTML = `
                        <img src="${attachment.download_url}" alt="${attachment.name}" style="
                            max-width:200px;
                            max-height:200px;
                            border-radius:8px;
                            cursor:pointer;
                        " onclick="window.open('${attachment.download_url}', '_blank')">
                    `;
                    attachmentsDiv.appendChild(imgDiv);
                } else if (attachment.mimetype.startsWith('audio/')) {
                    const audioDiv = document.createElement('div');
                    audioDiv.style.cssText = 'margin:4px 0;';
                    audioDiv.innerHTML = `
                        <div style="display:flex;align-items:center;gap:8px;padding:8px;background:rgba(255,255,255,0.1);border-radius:8px;">
                            <span style="font-size:16px;">🎵</span>
                            <div style="flex:1;">
                                <div style="font-weight:600;color:${isUser ? 'white' : '#333'};font-size:13px;">Voice Message</div>
                                <audio controls style="width:100%;height:30px;">
                                    <source src="${attachment.download_url}" type="${attachment.mimetype}">
                                </audio>
                            </div>
                        </div>
                    `;
                    attachmentsDiv.appendChild(audioDiv);
                } else {
                    // Regular file attachment
                    const attachmentDiv = document.createElement('div');
                    attachmentDiv.className = 'attachment-item';
                    attachmentDiv.style.cssText = `
                        display:flex;
                        align-items:center;
                        gap:8px;
                        padding:8px;
                        margin:4px 0;
                        background:rgba(255,255,255,0.1);
                        border-radius:8px;
                        border:1px solid rgba(255,255,255,0.2);
                    `;
                    
                    const icon = getFileIcon(attachment.mimetype);
                    
                    attachmentDiv.innerHTML = `
                        <span style="font-size:16px;">${icon}</span>
                        <div style="flex:1;min-width:0;">
                            <div style="font-weight:600;color:${isUser ? 'white' : '#333'};font-size:13px;">${attachment.name}</div>
                            <div style="font-size:11px;color:${isUser ? 'rgba(255,255,255,0.8)' : '#666'};">${formatFileSize(attachment.size)}</div>
                        </div>
                        <a href="${attachment.download_url}" target="_blank" class="attachment-link" style="
                            padding:4px 8px;
                            background:${isUser ? 'rgba(255,255,255,0.2)' : '#667eea'};
                            color:${isUser ? 'white' : 'white'};
                            text-decoration:none;
                            border-radius:4px;
                            font-size:11px;
                            font-weight:600;
                        ">Download</a>
                    `;
                    
                    attachmentsDiv.appendChild(attachmentDiv);
                }
            });
            
            messageDiv.appendChild(attachmentsDiv);
        }
        
        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    
    function getFileIcon(mimetype) {
        if (mimetype.startsWith('image/')) return '🖼️';
        if (mimetype.startsWith('video/')) return '🎥';
        if (mimetype.startsWith('audio/')) return '🎵';
        if (mimetype.includes('pdf')) return '📄';
        if (mimetype.includes('word') || mimetype.includes('document')) return '📝';
        if (mimetype.includes('excel') || mimetype.includes('spreadsheet')) return '📊';
        if (mimetype.includes('powerpoint') || mimetype.includes('presentation')) return '📋';
        if (mimetype.includes('zip') || mimetype.includes('rar') || mimetype.includes('archive')) return '📦';
        return '📎';
    }
    
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    function connectWebSocket() {
        if (!sessionId) return;
        
        websocket = new WebSocket(`${CONFIG.WS_BASE}/ws/${sessionId}`);
        
        websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('WebSocket message received:', data);
            
            if (data.type === 'message') {
                console.log('Message attachments:', data.data.attachments);
                let messageText = data.data.body ? `${data.data.author}: ${data.data.body}` : `${data.data.author}:`;
                
                if (!data.data.body && data.data.attachments && data.data.attachments.length > 0) {
                    const att = data.data.attachments[0];
                    if (att.mimetype.startsWith('audio/')) {
                        messageText = `${data.data.author} sent a voice message`;
                    } else if (att.mimetype.startsWith('image/')) {
                        messageText = `${data.data.author} sent an image`;
                    } else {
                        messageText = `${data.data.author} sent ${data.data.attachments.length} file(s)`;
                    }
                }
                
                addMessage(messageText, false, false, data.data.attachments || []);
            } else if (data.type === 'agent_joined') {
                addMessage(data.message, false, true);
            } else if (data.type === 'session_ended') {
                addMessage(data.message, false, true);
                sessionEnded = true;
                document.getElementById('message-input').disabled = true;
                document.getElementById('send-btn').disabled = true;
                
                // Show feedback survey after 2 seconds
                setTimeout(() => {
                    showFeedbackSurvey();
                }, 2000);
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
                startSessionMonitoring();
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
        .attachment-link:hover { opacity: 0.8 !important; }
        .attachment-item { transition: background-color 0.2s ease !important; }
        .attachment-item:hover { background: rgba(255,255,255,0.15) !important; }
        @media (max-width: 480px) {
            #chat-container.maximized { width: calc(100vw - 40px) !important; height: calc(100vh - 40px) !important; bottom: 20px !important; right: 20px !important; left: 20px !important; }
        }
    `;
    document.head.appendChild(style);

    // Initialize widget
    const widget = createWidget();
    addMessage('Hello! How can I help you today?');
    


    let monitoringInterval = null;

    let lastMessageId = 0;
    
    function startSessionMonitoring() {
        if (monitoringInterval || !sessionId) return;
        
        monitoringInterval = setInterval(async () => {
            if (sessionEnded) {
                clearInterval(monitoringInterval);
                return;
            }
            
            try {
                // Get messages to check for agent left
                const response = await fetch(`${CONFIG.API_BASE}/messages/${sessionId}`);
                const data = await response.json();
                
                if (data.messages && data.messages.length > 0) {
                    const sortedMessages = data.messages.sort((a, b) => a.id - b.id);
                    
                    sortedMessages.forEach(msg => {
                        if (msg.id > lastMessageId) {
                            // Check if agent left the conversation
                            if (msg.body.includes('left the channel') || msg.body.includes('left the conversation')) {
                                sessionEnded = true;
                                addMessage('Agent left the channel', false, true);
                                document.getElementById('message-input').disabled = true;
                                document.getElementById('send-btn').disabled = true;
                                clearInterval(monitoringInterval);
                                
                                // Show feedback survey after 2 seconds
                                setTimeout(() => {
                                    showFeedbackSurvey();
                                }, 2000);
                            }
                            // Skip feedback messages (don't show to visitor)
                            else if (!msg.body.includes('Customer Feedback:')) {
                                // Don't add regular messages here - they come via WebSocket
                            }
                            lastMessageId = msg.id;
                        }
                    });
                }
            } catch (error) {
                // Continue monitoring on error
            }
        }, 1500); // Check every 1.5 seconds like working code
    }

    function showFeedbackSurvey() {
        // Auto-maximize widget to show survey
        if (isMinimized) {
            toggleMinimize();
        }
        
        const messagesDiv = document.getElementById('chat-messages');
        if (!messagesDiv) return;
        
        const surveyDiv = document.createElement('div');
        surveyDiv.style.cssText = 'background: white; padding: 20px; border-radius: 12px; margin: 15px 0; box-shadow: 0 4px 12px rgba(0,0,0,0.15); border: 1px solid #e0e0e0; text-align: center;';
        
        surveyDiv.innerHTML = `
            <div style="margin-bottom: 15px; text-align: center;">
                <div style="font-size: 32px; margin-bottom: 10px;">💬</div>
                <h3 style="margin: 0 0 8px 0; font-size: 18px; color: #333; font-weight: 600;">Conversation ended</h3>
                <p style="margin: 0; font-size: 14px; color: #666;">Please rate the quality of this conversation</p>
            </div>
            <div style="display: flex; justify-content: center; gap: 5px; margin-bottom: 15px;" id="star-rating">
                <span class="rating-star" data-rating="1" style="font-size: 28px; cursor: pointer; color: #ddd; transition: color 0.2s;">★</span>
                <span class="rating-star" data-rating="2" style="font-size: 28px; cursor: pointer; color: #ddd; transition: color 0.2s;">★</span>
                <span class="rating-star" data-rating="3" style="font-size: 28px; cursor: pointer; color: #ddd; transition: color 0.2s;">★</span>
                <span class="rating-star" data-rating="4" style="font-size: 28px; cursor: pointer; color: #ddd; transition: color 0.2s;">★</span>
                <span class="rating-star" data-rating="5" style="font-size: 28px; cursor: pointer; color: #ddd; transition: color 0.2s;">★</span>
            </div>
            <textarea id="feedback-comment" placeholder="Leave a comment (optional)" style="width: calc(100% - 16px); height: 60px; padding: 8px; border: 1px solid #ddd; border-radius: 4px; resize: none; font-family: inherit; margin-bottom: 15px; font-size: 14px;"></textarea>
            <div style="display: flex; justify-content: center; gap: 10px;">
                <button onclick="submitFeedback()" style="padding: 8px 16px; background: #00a65a; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; font-weight: 500;">
                    Send
                </button>
                <button onclick="closeSurvey()" style="padding: 8px 16px; background: #f8f9fa; color: #6c757d; border: 1px solid #dee2e6; border-radius: 4px; cursor: pointer; font-size: 14px;">
                    Skip
                </button>
            </div>
        `;
        
        messagesDiv.appendChild(surveyDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        
        // Add star click handlers
        setTimeout(() => addStarHandlers(), 100);
    }

    let selectedRating = 0;

    window.selectRating = function(rating) {
        selectedRating = rating;
        const stars = document.querySelectorAll('.rating-star');
        stars.forEach((star, index) => {
            star.style.color = index < rating ? '#ffc107' : '#ddd';
        });
    }
    
    // Add click handlers after survey is created
    function addStarHandlers() {
        const stars = document.querySelectorAll('.rating-star');
        stars.forEach(star => {
            star.addEventListener('click', function() {
                const rating = parseInt(this.getAttribute('data-rating'));
                selectRating(rating);
            });
        });
    }

    window.submitFeedback = async function() {
        if (selectedRating === 0) {
            alert('Please select a rating');
            return;
        }
        
        const comment = document.getElementById('feedback-comment')?.value || '';
        
        try {
            await fetch(`${CONFIG.API_BASE}/feedback`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    session_id: sessionId,
                    rating: selectedRating,
                    comment: comment
                })
            });
            addMessage('Thank you for your feedback!', false, true);
        } catch (error) {
            addMessage('Thank you for your feedback!', false, true);
        }
        closeSurvey();
    }

    window.closeSurvey = function() {
        const survey = document.querySelector('#chat-messages div[style*="background: white"]');
        if (survey && survey.innerHTML.includes('Rate this conversation')) {
            survey.remove();
        }
        selectedRating = 0;
    }

    document.getElementById('send-btn').onclick = sendMessage;
    document.getElementById('message-input').onkeypress = (e) => {
        if (e.key === 'Enter') sendMessage();
    };
    document.getElementById('chat-header').onclick = toggleMinimize;
})();