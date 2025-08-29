(function() {
    const CONFIG = {
        API_BASE: 'https://ai.andrewdemo.online',
        WS_BASE: 'wss://ai.andrewdemo.online'
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
                <div id="chat-header" style="padding:0;background:transparent;color:white;font-weight:600;cursor:pointer;display:flex;justify-content:center;align-items:center;flex-shrink:0;width:100%;height:100%;position:relative;">
                    <span style="font-size:24px;">💬</span>
                    <div id="menu-btn" style="position:absolute;top:8px;right:8px;width:24px;height:24px;border-radius:50%;background:rgba(255,255,255,0.2);display:none;align-items:center;justify-content:center;cursor:pointer;font-size:12px;" onclick="event.stopPropagation();toggleMenu();">⋮</div>
                </div>
                <div id="chat-body" style="flex:1;display:none;flex-direction:column;background:white;min-height:0;">
                    <div id="chat-messages" style="flex:1;padding:20px;overflow-y:auto;background:linear-gradient(to bottom,#f8f9fa,#ffffff);min-height:0;"></div>
                    <div style="padding:16px 20px;background:white;border-top:1px solid #e9ecef;flex-shrink:0;">
                        <div style="display:flex;gap:8px;align-items:stretch;padding:0;">
                            <input type="text" id="message-input" placeholder="Type your message..." style="flex:1;padding:12px 16px;border:2px solid #e9ecef;border-radius:25px;outline:none;font-size:14px;transition:border-color 0.2s ease;min-width:0;">
                            <input type="file" id="file-input" style="display:none;" accept=".jpg,.jpeg,.png,.gif,.pdf,.doc,.docx,.txt,.zip,.mp3,.wav,.ogg,.mp4,.avi,.mov">
                            <button id="attach-btn" style="padding:12px;background:#f8f9fa;color:#666;border:1px solid #e9ecef;border-radius:50%;cursor:pointer;font-size:16px;width:48px;height:48px;display:none;flex-shrink:0;" title="Attach file">📄</button>
                            <button id="send-btn" style="padding:12px 16px;background:linear-gradient(135deg,#667eea,#764ba2);color:white;border:none;border-radius:25px;cursor:pointer;font-weight:600;transition:transform 0.2s ease;white-space:nowrap;flex-shrink:0;">Send</button>
                        </div>
                    </div>
                    <div id="menu-dropdown" style="position:absolute;top:60px;right:20px;background:white;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.15);border:1px solid #e9ecef;min-width:160px;display:none;z-index:10000;">
                        <div onclick="clearConversation()" style="padding:12px 16px;cursor:pointer;border-bottom:1px solid #f1f3f4;color:#333;font-size:14px;transition:background 0.2s;" onmouseover="this.style.background='#f8f9fa'" onmouseout="this.style.background='white'">⌫ Clear conversation</div>
                        <div onclick="endConversation()" style="padding:12px 16px;cursor:pointer;color:#dc3545;font-size:14px;transition:background 0.2s;" onmouseover="this.style.background='#f8f9fa'" onmouseout="this.style.background='white'">⏹ End conversation</div>
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
        return messageDiv;
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
        const fileInput = document.getElementById('file-input');
        const message = input.value.trim();
        const file = fileInput.files[0];
        
        if (!message && !file) return;
        if (sessionEnded) return;

        // Handle file upload if connected to agent
        if (file && sessionId) {
            await sendFileToAgent(file, message);
            input.value = '';
            fileInput.value = '';
            return;
        }
        
        // Regular message handling
        if (!message) return;
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
                // Show attach button after connecting to agent
                document.getElementById('attach-btn').style.display = 'block';
            } else if (data.response) {
                addMessage(data.response);
            }
        } catch (error) {
            addMessage('Sorry, there was an error. Please try again.');
        }
    }
    
    async function sendFileToAgent(file, message = '') {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('session_id', sessionId);
        if (message) formData.append('message', message);
        
        // Show uploading message
        const uploadMsg = message ? `${message} (uploading ${file.name}...)` : `Uploading ${file.name}...`;
        const uploadMsgElement = addMessage(uploadMsg, true);
        
        try {
            const response = await fetch(`${CONFIG.API_BASE}/upload-file`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                // Remove uploading message and show success
                uploadMsgElement.remove();
                const successMsg = message ? `${message} ${file.name}` : file.name;
                addMessage(successMsg, true);
            } else {
                uploadMsgElement.remove();
                addMessage('Failed to upload file. Please try again.');
            }
        } catch (error) {
            uploadMsgElement.remove();
            addMessage('Failed to upload file. Please try again.');
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
            document.getElementById('menu-btn').style.display = 'flex';
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
            document.getElementById('menu-btn').style.display = 'none';
            document.getElementById('menu-dropdown').style.display = 'none';
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
        #menu-btn:hover { background: rgba(255,255,255,0.3) !important; }
        @media (max-width: 480px) {
            #chat-container.maximized { width: calc(100vw - 20px) !important; height: calc(100vh - 80px) !important; bottom: 10px !important; right: 10px !important; left: 10px !important; }
            #chat-container { bottom: 10px !important; right: 10px !important; }
            #send-btn { padding: 12px 12px !important; font-size: 13px !important; }
            #message-input { font-size: 16px !important; }
        }
        @media (max-width: 360px) {
            #chat-container.maximized { width: calc(100vw - 10px) !important; height: calc(100vh - 60px) !important; bottom: 5px !important; right: 5px !important; left: 5px !important; }
            #send-btn { padding: 12px 8px !important; min-width: 50px !important; }
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
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="width: 48px; height: 48px; background: linear-gradient(135deg, #667eea, #764ba2); border-radius: 50%; margin: 0 auto 12px; display: flex; align-items: center; justify-content: center; color: white; font-size: 20px;">✓</div>
                <h3 style="margin: 0 0 6px 0; font-size: 16px; color: #2c3e50; font-weight: 600;">Conversation Complete</h3>
                <p style="margin: 0; font-size: 13px; color: #7f8c8d; line-height: 1.4;">How would you rate your experience?</p>
            </div>
            <div style="display: flex; justify-content: center; gap: 8px; margin-bottom: 16px; padding: 0 10px;" id="star-rating">
                <span class="rating-star" data-rating="1" style="font-size: 24px; cursor: pointer; color: #e0e0e0; transition: all 0.2s ease;">★</span>
                <span class="rating-star" data-rating="2" style="font-size: 24px; cursor: pointer; color: #e0e0e0; transition: all 0.2s ease;">★</span>
                <span class="rating-star" data-rating="3" style="font-size: 24px; cursor: pointer; color: #e0e0e0; transition: all 0.2s ease;">★</span>
                <span class="rating-star" data-rating="4" style="font-size: 24px; cursor: pointer; color: #e0e0e0; transition: all 0.2s ease;">★</span>
                <span class="rating-star" data-rating="5" style="font-size: 24px; cursor: pointer; color: #e0e0e0; transition: all 0.2s ease;">★</span>
            </div>
            <textarea id="feedback-comment" placeholder="Share your thoughts (optional)" style="width: calc(100% - 20px); height: 50px; padding: 10px; border: 1px solid #e1e8ed; border-radius: 8px; resize: none; font-family: inherit; margin-bottom: 16px; font-size: 13px; background: #fafbfc; outline: none; transition: border-color 0.2s;"></textarea>
            <div style="display: flex; gap: 8px;">
                <button onclick="submitFeedback()" style="flex: 1; padding: 10px 16px; background: linear-gradient(135deg, #667eea, #764ba2); color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 500; transition: opacity 0.2s;" onmouseover="this.style.opacity='0.9'" onmouseout="this.style.opacity='1'">
                    Submit
                </button>
                <button onclick="closeSurvey()" style="flex: 1; padding: 10px 16px; background: #f8f9fa; color: #6c757d; border: 1px solid #e9ecef; border-radius: 6px; cursor: pointer; font-size: 13px; transition: background 0.2s;" onmouseover="this.style.background='#e9ecef'" onmouseout="this.style.background='#f8f9fa'">
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
            star.style.color = index < rating ? '#ffd700' : '#e0e0e0';
            star.style.transform = index < rating ? 'scale(1.1)' : 'scale(1)';
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
        
        // Fade out survey
        const surveys = document.querySelectorAll('#chat-messages > div');
        surveys.forEach(survey => {
            if (survey.innerHTML && (survey.innerHTML.includes('Conversation Complete') || survey.innerHTML.includes('rate your experience'))) {
                survey.style.transition = 'opacity 0.3s ease';
                survey.style.opacity = '0';
                setTimeout(() => survey.remove(), 300);
            }
        });
        
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
            setTimeout(() => addMessage('Thank you for your feedback!', false, true), 300);
        } catch (error) {
            setTimeout(() => addMessage('Thank you for your feedback!', false, true), 300);
        }
        selectedRating = 0;
    }

    window.closeSurvey = function() {
        const surveys = document.querySelectorAll('#chat-messages > div');
        surveys.forEach(survey => {
            if (survey.innerHTML && (survey.innerHTML.includes('Conversation Complete') || survey.innerHTML.includes('rate your experience'))) {
                survey.style.transition = 'opacity 0.3s ease';
                survey.style.opacity = '0';
                setTimeout(() => survey.remove(), 300);
            }
        });
        selectedRating = 0;
    }
    
    window.toggleMenu = function() {
        const menu = document.getElementById('menu-dropdown');
        menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
    }
    
    window.clearConversation = function() {
        const messagesDiv = document.getElementById('chat-messages');
        messagesDiv.innerHTML = '';
        addMessage('Conversation cleared. How can I help you?');
        document.getElementById('menu-dropdown').style.display = 'none';
    }
    
    window.endConversation = async function() {
        document.getElementById('menu-dropdown').style.display = 'none';
        
        if (sessionId) {
            try {
                await fetch(`${CONFIG.API_BASE}/end-session`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({session_id: sessionId})
                });
            } catch (error) {
                console.log('Error ending session:', error);
            }
            
            addMessage('You ended the conversation', false, true);
            sessionEnded = true;
            document.getElementById('message-input').disabled = true;
            document.getElementById('send-btn').disabled = true;
            document.getElementById('attach-btn').style.display = 'none';
            
            setTimeout(() => {
                showFeedbackSurvey();
            }, 2000);
        } else {
            // End AI-only conversation and show feedback
            addMessage('You ended the conversation', false, true);
            sessionEnded = true;
            document.getElementById('message-input').disabled = true;
            document.getElementById('send-btn').disabled = true;
            
            setTimeout(() => {
                showFeedbackSurvey();
            }, 2000);
        }
    }
    
    // Close menu when clicking outside
    document.addEventListener('click', function(event) {
        const menu = document.getElementById('menu-dropdown');
        const menuBtn = document.getElementById('menu-btn');
        if (menu && !menu.contains(event.target) && !menuBtn.contains(event.target)) {
            menu.style.display = 'none';
        }
    });

    document.getElementById('send-btn').onclick = sendMessage;
    document.getElementById('message-input').onkeypress = (e) => {
        if (e.key === 'Enter') sendMessage();
    };
    document.getElementById('attach-btn').onclick = () => {
        document.getElementById('file-input').click();
    };
    document.getElementById('file-input').onchange = (e) => {
        if (e.target.files[0] && sessionId) {
            // Auto-send file when selected (if connected to agent)
            sendMessage();
        }
    };
    document.getElementById('chat-header').onclick = function(e) {
        if (e.target.id !== 'menu-btn') {
            toggleMinimize();
        }
    };
})();