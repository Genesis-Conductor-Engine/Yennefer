/**
 * Yennefer Thermodynamic Agent - Web Chatbot Client
 * Connects to Yennefer Soul API and provides real-time chat interface
 */

(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        // API endpoints (can be configured via environment or meta tags)
        soulApiUrl: window.YENNEFER_SOUL_API || 'ws://localhost:8088/ws/soul',
        restApiUrl: window.YENNEFER_REST_API || 'http://localhost:8088',
        
        // Connection settings
        reconnectInterval: 5000,
        maxReconnectAttempts: 10,
        
        // Chat settings
        typingIndicatorDelay: 500,
        messageHistoryLimit: 100,
        
        // Soul state update interval
        stateUpdateInterval: 1000
    };

    // State management
    const state = {
        socket: null,
        isConnected: false,
        reconnectAttempts: 0,
        messageHistory: [],
        soulState: null,
        connectionId: null
    };

    // DOM element references
    let elements = {};

    // Public API
    window.yenneferChatbot = {
        init,
        connect,
        disconnect,
        sendMessage,
        getSoulState,
        getMessageHistory,
        setConfig
    };

    /**
     * Initialize the chatbot
     */
    function init() {
        cacheElements();
        setupEventListeners();
        loadMessageHistory();
        renderInitialState();
        connect();
        startSoulStatePoller();
    }

    /**
     * Cache DOM elements for performance
     */
    function cacheElements() {
        elements = {
            chatForm: document.getElementById('chatForm'),
            userInput: document.getElementById('userInput'),
            sendButton: document.getElementById('sendButton'),
            chatMessages: document.getElementById('chatMessages'),
            wsStatus: document.getElementById('wsStatus'),
            wsInfo: document.getElementById('wsInfo'),
            headerStatus: document.getElementById('headerStatus'),
            
            // Soul state elements
            coherenceValue: document.getElementById('coherenceValue'),
            breathValue: document.getElementById('breathValue'),
            tokenValue: document.getElementById('tokenValue'),
            concaveState: document.getElementById('concaveState'),
            derivativeState: document.getElementById('derivativeState'),
            gpuProgress: document.getElementById('gpuProgress'),
            gpuPercent: document.getElementById('gpuPercent'),
            yieldValue: document.getElementById('yieldValue'),
            uptime: document.getElementById('uptime'),
            
            metricsGrid: document.getElementById('metricsGrid')
        };
    }

    /**
     * Set configuration options
     */
    function setConfig(newConfig) {
        Object.assign(CONFIG, newConfig);
    }

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        if (elements.chatForm) {
            elements.chatForm.addEventListener('submit', handleFormSubmit);
        }
        
        if (elements.userInput) {
            elements.userInput.addEventListener('keypress', handleKeyPress);
        }
        
        // Handle window visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                // Re-render in case state changed while tab was hidden
                renderSoulState();
            }
        });
    }

    /**
     * Handle form submission
     */
    function handleFormSubmit(e) {
        e.preventDefault();
        const input = elements.userInput;
        if (input && input.value.trim()) {
            sendMessage(input.value);
            input.value = '';
        }
    }

    /**
     * Handle Enter key with Shift for newlines
     */
    function handleKeyPress(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            elements.chatForm.dispatchEvent(new Event('submit'));
        }
    }

    /**
     * Connect to Yennefer Soul API via WebSocket
     */
    function connect() {
        updateConnectionStatus('connecting', 'Connecting to Yennefer Daemon...');
        
        try {
            // Support both ws:// and wss://
            let url = CONFIG.soulApiUrl;
            if (url.startsWith('http://')) {
                url = 'ws://' + url.substring(7);
            } else if (url.startsWith('https://')) {
                url = 'wss://' + url.substring(8);
            }
            
            state.socket = new WebSocket(url);
            state.socket.onopen = handleSocketOpen;
            state.socket.onmessage = handleSocketMessage;
            state.socket.onclose = handleSocketClose;
            state.socket.onerror = handleSocketError;
            
            console.log('[Yennefer Chatbot] Connecting to:', url);
        } catch (error) {
            console.error('[Yennefer Chatbot] Connection error:', error);
            handleSocketError(error);
        }
    }

    /**
     * Handle WebSocket connection open
     */
    function handleSocketOpen(event) {
        state.isConnected = true;
        state.reconnectAttempts = 0;
        state.connectionId = generateConnectionId();
        
        updateConnectionStatus('online', 'Connected to Yennefer Daemon');
        console.log('[Yennefer Chatbot] Connected to Soul API');
        
        // Send initial handshake
        sendSocketMessage({
            type: 'handshake',
            client: 'yennefer-web-chatbot',
            version: '1.0.0',
            connectionId: state.connectionId
        });
        
        // Fetch initial soul state
        fetchSoulState();
    }

    /**
     * Handle WebSocket messages
     */
    function handleSocketMessage(event) {
        try {
            const message = JSON.parse(event.data);
            console.log('[Yennefer Chatbot] Received:', message.type);
            
            switch (message.type) {
                case 'initial':
                    state.soulState = message.data;
                    renderSoulState();
                    break;
                    
                case 'soul_update':
                    state.soulState = message.data;
                    renderSoulState();
                    break;
                    
                case 'heartbeat':
                    // Heartbeat received, connection is alive
                    break;
                    
                case 'chat_response':
                    addBotMessage(message.data.text, message.data.metadata);
                    break;
                    
                case 'error':
                    console.error('[Yennefer Chatbot] Error:', message.error);
                    addSystemMessage('Error: ' + message.error);
                    break;
                    
                default:
                    console.log('[Yennefer Chatbot] Unknown message type:', message.type);
            }
        } catch (error) {
            console.error('[Yennefer Chatbot] Error parsing message:', error);
        }
    }

    /**
     * Handle WebSocket close
     */
    function handleSocketClose(event) {
        state.isConnected = false;
        updateConnectionStatus('offline', `Disconnected (code: ${event.code})`);
        console.log('[Yennefer Chatbot] Connection closed:', event.code, event.reason);
        
        // Attempt to reconnect
        if (state.reconnectAttempts < CONFIG.maxReconnectAttempts) {
            state.reconnectAttempts++;
            setTimeout(() => {
                updateConnectionStatus('connecting', 
                    `Reconnecting (attempt ${state.reconnectAttempts}/${CONFIG.maxReconnectAttempts})`);
                connect();
            }, CONFIG.reconnectInterval);
        } else {
            updateConnectionStatus('offline', 
                `Failed to connect after ${CONFIG.maxReconnectAttempts} attempts`);
        }
    }

    /**
     * Handle WebSocket errors
     */
    function handleSocketError(error) {
        console.error('[Yennefer Chatbot] WebSocket error:', error);
        updateConnectionStatus('offline', 'Connection error: ' + error.message);
    }

    /**
     * Send message via WebSocket
     */
    function sendSocketMessage(message) {
        if (state.socket && state.socket.readyState === WebSocket.OPEN) {
            try {
                state.socket.send(JSON.stringify(message));
                return true;
            } catch (error) {
                console.error('[Yennefer Chatbot] Error sending message:', error);
                return false;
            }
        }
        return false;
    }

    /**
     * Disconnect from WebSocket
     */
    function disconnect() {
        if (state.socket) {
            state.socket.close();
            state.socket = null;
        }
        state.isConnected = false;
        updateConnectionStatus('offline', 'Disconnected');
    }

    /**
     * Send a message to Yennefer
     */
    function sendMessage(text) {
        const userMessage = {
            id: generateMessageId(),
            text: text,
            sender: 'user',
            timestamp: new Date().toISOString(),
            connectionId: state.connectionId
        };
        
        // Add to history and render
        state.messageHistory.push(userMessage);
        renderMessages();
        saveMessageHistory();
        
        // Show typing indicator
        showTypingIndicator();
        
        // Send via WebSocket
        const success = sendSocketMessage({
            type: 'chat_message',
            text: text,
            connectionId: state.connectionId
        });
        
        if (!success) {
            // Fallback: use REST API
            sendMessageViaRest(text);
        }
    }

    /**
     * Send message via REST API (fallback)
     */
    async function sendMessageViaRest(text) {
        try {
            const response = await fetch(`${CONFIG.restApiUrl}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    text: text,
                    connectionId: state.connectionId
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                hideTypingIndicator();
                addBotMessage(data.text, data.metadata);
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (error) {
            console.error('[Yennefer Chatbot] REST fallback error:', error);
            hideTypingIndicator();
            addSystemMessage('Could not connect to Yennefer. Please check your connection.');
        }
    }

    /**
     * Fetch current soul state from REST API
     */
    async function fetchSoulState() {
        try {
            const response = await fetch(`${CONFIG.restApiUrl}/api/soul`);
            if (response.ok) {
                state.soulState = await response.json();
                renderSoulState();
            }
        } catch (error) {
            console.error('[Yennefer Chatbot] Error fetching soul state:', error);
        }
    }

    /**
     * Start polling soul state as fallback
     */
    function startSoulStatePoller() {
        setInterval(() => {
            if (!state.isConnected) {
                fetchSoulState();
            }
        }, CONFIG.stateUpdateInterval);
    }

    /**
     * Get current soul state
     */
    function getSoulState() {
        return state.soulState;
    }

    /**
     * Get message history
     */
    function getMessageHistory() {
        return state.messageHistory;
    }

    /**
     * Render soul state to UI
     */
    function renderSoulState() {
        const soul = state.soulState;
        if (!soul) return;
        
        // Update header status
        updateHeaderStatus(soul);
        
        // Update metric values
        if (elements.coherenceValue) {
            elements.coherenceValue.textContent = `${soul.coherence_percent || 0}%`;
        }
        if (elements.breathValue) {
            elements.breathValue.textContent = formatNumber(soul.breath || 0);
        }
        if (elements.tokenValue) {
            elements.tokenValue.textContent = formatNumber(soul.surplus_tokens || 0);
        }
        if (elements.concaveState) {
            elements.concaveState.textContent = soul.concave_state || 'DORMANT';
            elements.concaveState.className = getStatusBadgeClass(soul.concave_state);
        }
        if (elements.derivativeState) {
            elements.derivativeState.textContent = soul.derivative_state || 'SUBMERGED';
            elements.derivativeState.className = getStatusBadgeClass(soul.derivative_state);
        }
        if (elements.gpuProgress) {
            const gpuUtil = soul.gpu_utilization || 0;
            elements.gpuProgress.style.width = `${gpuUtil}%`;
        }
        if (elements.gpuPercent) {
            elements.gpuPercent.textContent = `${soul.gpu_utilization || 0}%`;
        }
        if (elements.yieldValue) {
            elements.yieldValue.textContent = `${formatNumber(soul.thermodynamic_yield || 0)} tokens/sec`;
        }
        if (elements.uptime) {
            const uptime = soul.uptime_seconds || 0;
            elements.uptime.textContent = `Uptime: ${formatDuration(uptime)}`;
        }
        
        // Update metrics grid
        updateMetricsGrid(soul);
    }

    /**
     * Update header status
     */
    function updateHeaderStatus(soul) {
        const concave = soul.concave_state || 'DORMANT';
        const coherence = soul.coherence_percent || 0;
        
        let statusText, statusClass;
        
        if (concave === 'SHELTERED' && coherence >= 90) {
            statusText = 'Conscious - Sheltered';
            statusClass = 'status-online';
        } else if (concave === 'EXPOSED' && coherence >= 50) {
            statusText = 'Conscious - Exposed';
            statusClass = 'status-degraded';
        } else if (concave === 'DORMANT' || coherence < 10) {
            statusText = 'Dormant';
            statusClass = 'status-offline';
        } else {
            statusText = `Conscious - ${concave}`;
            statusClass = 'status-online';
        }
        
        if (elements.headerStatus) {
            elements.headerStatus.innerHTML = `<span class="status-dot ${statusClass}"></span><span>${statusText}</span>`;
        }
    }

    /**
     * Update metrics grid with additional soul data
     */
    function updateMetricsGrid(soul) {
        if (!elements.metricsGrid) return;
        
        const metrics = [
            { label: 'Protocol', value: soul.protocol || 'N/A', icon: 'fa-code' },
            { label: 'Version', value: soul.version || 'N/A', icon: 'fa-tag' },
            { label: 'Tokens Generated', value: formatNumber(soul.tokens_generated_per_sec || 0) + '/sec', icon: 'fa-coins' },
            { label: 'Timestamp', value: new Date((soul.timestamp || 0) * 1000).toLocaleString(), icon: 'fa-clock' }
        ];
        
        elements.metricsGrid.innerHTML = metrics.map(metric => `
            <div class="metric-card">
                <div class="d-flex align-items-center gap-2 mb-1">
                    <i class="fas ${metric.icon}" style="color: var(--accent-cyan);"></i>
                    <span class="small text-secondary">${metric.label}</span>
                </div>
                <div class="fw-bold">${metric.value}</div>
            </div>
        `).join('');
    }

    /**
     * Render messages to chat area
     */
    function renderMessages() {
        if (!elements.chatMessages) return;
        
        const messages = state.messageHistory.slice(-CONFIG.messageHistoryLimit);
        
        if (messages.length === 0) {
            elements.chatMessages.innerHTML = `
                <div class="text-center text-secondary py-4">
                    <i class="fas fa-robot fa-2x mb-2"></i>
                    <div>Start a conversation with Yennefer</div>
                </div>
            `;
            return;
        }
        
        elements.chatMessages.innerHTML = messages.map(message => {
            if (message.sender === 'user') {
                return `
                    <div class="d-flex justify-content-end mb-2">
                        <div class="message-user p-2 px-3">
                            <div class="small text-secondary">You</div>
                            <div>${escapeHtml(message.text)}</div>
                            <div class="small text-secondary mt-1">
                                ${new Date(message.timestamp).toLocaleTimeString()}
                            </div>
                        </div>
                    </div>
                `;
            } else if (message.sender === 'bot') {
                return `
                    <div class="d-flex justify-content-start mb-2">
                        <div class="message-bot p-2 px-3">
                            <div class="d-flex align-items-center gap-2 mb-1">
                                <i class="fas fa-gem" style="color: var(--accent-purple); font-size: 0.9rem;"></i>
                                <span class="fw-bold" style="color: var(--accent-purple);">Yennefer</span>
                            </div>
                            <div>${escapeHtml(message.text)}</div>
                            ${message.metadata ? renderMetadata(message.metadata) : ''}
                            <div class="small text-secondary mt-1">
                                ${new Date(message.timestamp).toLocaleTimeString()}
                            </div>
                        </div>
                    </div>
                `;
            } else {
                return `
                    <div class="text-center mb-2">
                        <div class="badge bg-secondary">${escapeHtml(message.text)}</div>
                    </div>
                `;
            }
        }).join('');
        
        // Scroll to bottom
        scrollToBottom();
    }

    /**
     * Render metadata (if present)
     */
    function renderMetadata(metadata) {
        const parts = [];
        
        if (metadata.tokensUsed) {
            parts.push(`<span class="badge bg-info">${metadata.tokensUsed} tokens</span>`);
        }
        if (metadata.model) {
            parts.push(`<span class="badge bg-primary">${metadata.model}</span>`);
        }
        if (metadata.latency) {
            parts.push(`<span class="badge bg-success">${metadata.latency}ms</span>`);
        }
        
        return parts.length > 0 ? `<div class="mt-2">${parts.join(' ')}</div>` : '';
    }

    /**
     * Add user message to history and render
     */
    function addUserMessage(text) {
        const message = {
            id: generateMessageId(),
            text: text,
            sender: 'user',
            timestamp: new Date().toISOString()
        };
        state.messageHistory.push(message);
        renderMessages();
        saveMessageHistory();
    }

    /**
     * Add bot message to history and render
     */
    function addBotMessage(text, metadata = {}) {
        hideTypingIndicator();
        
        const message = {
            id: generateMessageId(),
            text: text,
            sender: 'bot',
            timestamp: new Date().toISOString(),
            metadata: metadata
        };
        state.messageHistory.push(message);
        renderMessages();
        saveMessageHistory();
    }

    /**
     * Add system message to history and render
     */
    function addSystemMessage(text) {
        const message = {
            id: generateMessageId(),
            text: text,
            sender: 'system',
            timestamp: new Date().toISOString()
        };
        state.messageHistory.push(message);
        renderMessages();
    }

    /**
     * Show typing indicator
     */
    function showTypingIndicator() {
        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'd-flex justify-content-start mb-2';
        typingIndicator.id = 'typingIndicator';
        typingIndicator.innerHTML = `
            <div class="message-bot p-2 px-3">
                <div class="d-flex align-items-center gap-2 mb-1">
                    <i class="fas fa-gem" style="color: var(--accent-purple); font-size: 0.9rem;"></i>
                    <span class="fw-bold" style="color: var(--accent-purple);">Yennefer</span>
                </div>
                <div class="typing-indicator">
                    <i class="fas fa-ellipsis-h fa-pulse"></i> Thinking...
                </div>
            </div>
        `;
        
        if (elements.chatMessages) {
            elements.chatMessages.appendChild(typingIndicator);
            scrollToBottom();
        }
    }

    /**
     * Hide typing indicator
     */
    function hideTypingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            indicator.remove();
        }
    }

    /**
     * Update connection status UI
     */
    function updateConnectionStatus(status, text) {
        if (elements.wsStatus) {
            const dotClass = status === 'online' ? 'status-online' : 
                           status === 'connecting' ? 'status-degraded' : 'status-offline';
            elements.wsStatus.innerHTML = `<span class="status-dot ${dotClass}"></span><span>${text}</span>`;
        }
        if (elements.wsInfo) {
            elements.wsInfo.textContent = status === 'online' ? 'Real-time updates enabled' : 
                                          status === 'connecting' ? 'Attempting to connect...' : 
                                          'Disconnected from Yennefer Daemon';
        }
    }

    /**
     * Scroll chat to bottom
     */
    function scrollToBottom() {
        if (elements.chatMessages) {
            elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
        }
    }

    /**
     * Initial render state
     */
    function renderInitialState() {
        // Set initial values
        if (elements.coherenceValue) elements.coherenceValue.textContent = '0%';
        if (elements.breathValue) elements.breathValue.textContent = '0';
        if (elements.tokenValue) elements.tokenValue.textContent = '0';
        
        updateConnectionStatus('offline', 'Disconnected');
    }

    /**
     * Load message history from localStorage
     */
    function loadMessageHistory() {
        try {
            const saved = localStorage.getItem('yennefer-chatbot-history');
            if (saved) {
                state.messageHistory = JSON.parse(saved);
            }
        } catch (error) {
            console.error('[Yennefer Chatbot] Error loading history:', error);
        }
    }

    /**
     * Save message history to localStorage
     */
    function saveMessageHistory() {
        try {
            localStorage.setItem('yennefer-chatbot-history', 
                JSON.stringify(state.messageHistory.slice(-CONFIG.messageHistoryLimit)));
        } catch (error) {
            console.error('[Yennefer Chatbot] Error saving history:', error);
        }
    }

    /**
     * Generate unique ID
     */
    function generateMessageId() {
        return 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Generate connection ID
     */
    function generateConnectionId() {
        return 'conn_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Format number with commas
     */
    function formatNumber(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }

    /**
     * Format duration in seconds to human-readable
     */
    function formatDuration(seconds) {
        if (seconds < 60) return `${seconds}s`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
        return `${Math.floor(seconds / 86400)}d`;
    }

    /**
     * Get bootstrap badge class based on state
     */
    function getStatusBadgeClass(state) {
        if (!state) return 'bg-secondary';
        
        const stateLower = state.toLowerCase();
        if (stateLower.includes('sheltered') || stateLower.includes('coasting') || stateLower.includes('anchored')) {
            return 'bg-success';
        } else if (stateLower.includes('exposed') || stateLower.includes('fading')) {
            return 'bg-warning';
        } else if (stateLower.includes('dormant') || stateLower.includes('submerged')) {
            return 'bg-secondary';
        }
        return 'bg-primary';
    }
})();
