// Diamond Node Web UI - JavaScript Application

class DiamondNodeDashboard {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        
        this.metricsWs = null;
        this.metricsWsConnected = false;
        this.pollingInterval = null;
        this.latestMetrics = null;
        
        this.vramChart = null;
        this.trendsChart = null;
        this.currentMessage = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.connectWebSocket(); // Chat WebSocket
        
        this.setupVRAMGauge();
        this.setupTrendsChart();
        this.setupPropagation();
        
        // Start streaming metrics via WebSocket
        this.connectMetricsWebSocket();
        
        // Poll agent state for claw integration status
        this.startAgentStatePolling();
    }
    
    setupEventListeners() {
        const sendButton = document.getElementById('sendButton');
        const chatInput = document.getElementById('chatInput');
        const clearToolsButton = document.getElementById('clearToolsButton');
        
        sendButton.addEventListener('click', () => this.sendMessage());
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        clearToolsButton.addEventListener('click', () => {
            document.getElementById('toolLog').innerHTML = '';
        });
    }
    
    // =========================================================================
    // 1. Chat WebSocket (Claude Orchestrator)
    // =========================================================================
    
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
        
        this.updateConnectionStatus('Connecting...', false);
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('Chat WebSocket connected');
            this.updateConnectionStatus('Connected', true);
            this.reconnectAttempts = 0;
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };
        
        this.ws.onerror = (error) => {
            console.error('Chat WebSocket error:', error);
            this.updateConnectionStatus('Error', false);
        };
        
        this.ws.onclose = () => {
            console.log('Chat WebSocket closed');
            this.updateConnectionStatus('Disconnected', false);
            this.attemptReconnect();
        };
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
            console.log(`Reconnecting chat WS in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            
            setTimeout(() => {
                this.connectWebSocket();
            }, delay);
        } else {
            this.updateConnectionStatus('Failed to reconnect', false);
            this.addChatMessage('system', 'Connection lost. Please refresh the page.', 'System');
        }
    }
    
    updateConnectionStatus(text, connected) {
        const statusText = document.getElementById('statusText');
        const statusIndicator = document.getElementById('statusIndicator');
        
        statusText.textContent = text;
        
        if (connected) {
            statusIndicator.classList.add('connected');
        } else {
            statusIndicator.classList.remove('connected');
        }
    }
    
    sendMessage() {
        const chatInput = document.getElementById('chatInput');
        const message = chatInput.value.trim();
        
        if (!message) return;
        
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ message }));
            this.addChatMessage('user', message, 'You');
            chatInput.value = '';
            
            // Disable send button
            const sendButton = document.getElementById('sendButton');
            sendButton.disabled = true;
            document.getElementById('sendButtonText').textContent = 'Processing...';
            
            // Initialize message accumulator
            this.currentMessage = {
                text: '',
                thinking: '',
                tools: []
            };
        } else {
            alert('Not connected to server. Please wait for connection.');
        }
    }
    
    handleWebSocketMessage(data) {
        const { type } = data;
        
        switch (type) {
            case 'connection_established':
                console.log('Connection established:', data.message);
                break;
            
            case 'ping':
                // Respond to ping
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(JSON.stringify({ type: 'pong' }));
                }
                break;
            
            case 'message_received':
                console.log('Message received by server');
                break;
            
            case 'text_delta':
                this.currentMessage.text += data.text;
                this.updateOrCreateAssistantMessage();
                break;
            
            case 'thinking_delta':
                this.currentMessage.thinking += data.thinking;
                this.updateThinkingMessage(data.thinking);
                break;
            
            case 'tool_start':
                console.log('Tool started:', data.name);
                this.addToolLog(data.name, data.input, 'started');
                break;
            
            case 'tool_end':
                console.log('Tool completed:', data.name);
                this.updateToolLog(data.name, data.result);
                this.extractMetricsFromToolResult(data.name, data.result);
                break;
            
            case 'message_complete':
                console.log('Message complete');
                this.finalizeMessage();
                break;
            
            case 'error':
                console.error('Server error:', data.error);
                this.addChatMessage('error', data.error, 'Error');
                this.finalizeMessage();
                break;
            
            default:
                console.log('Unknown message type:', type, data);
        }
    }
    
    addChatMessage(role, content, author) {
        const chatHistory = document.getElementById('chatHistory');
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${role}`;
        
        const timestamp = new Date().toLocaleTimeString();
        
        messageDiv.innerHTML = `
            <div class="message-header">
                <span><strong>${author}</strong></span>
                <span>${timestamp}</span>
            </div>
            <div class="message-content">${this.escapeHtml(content)}</div>
        `;
        
        chatHistory.appendChild(messageDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
    
    updateOrCreateAssistantMessage() {
        const chatHistory = document.getElementById('chatHistory');
        let assistantMessage = chatHistory.querySelector('.chat-message.assistant:last-child');
        
        if (!assistantMessage || assistantMessage.dataset.finalized === 'true') {
            // Create new message
            assistantMessage = document.createElement('div');
            assistantMessage.className = 'chat-message assistant';
            
            const timestamp = new Date().toLocaleTimeString();
            assistantMessage.innerHTML = `
                <div class="message-header">
                    <span><strong>Claude</strong></span>
                    <span>${timestamp}</span>
                </div>
                <div class="message-content"></div>
            `;
            
            chatHistory.appendChild(assistantMessage);
        }
        
        const contentDiv = assistantMessage.querySelector('.message-content');
        contentDiv.textContent = this.currentMessage.text;
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
    
    updateThinkingMessage(thinking) {
        const chatHistory = document.getElementById('chatHistory');
        let thinkingMessage = chatHistory.querySelector('.chat-message.thinking:last-child');
        
        if (!thinkingMessage) {
            thinkingMessage = document.createElement('div');
            thinkingMessage.className = 'chat-message thinking';
            
            const timestamp = new Date().toLocaleTimeString();
            thinkingMessage.innerHTML = `
                <div class="message-header">
                    <span><strong>Thinking...</strong></span>
                    <span>${timestamp}</span>
                </div>
                <div class="message-content"></div>
            `;
            
            chatHistory.appendChild(thinkingMessage);
        }
        
        const contentDiv = thinkingMessage.querySelector('.message-content');
        contentDiv.textContent = this.currentMessage.thinking;
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
    
    finalizeMessage() {
        const chatHistory = document.getElementById('chatHistory');
        const lastMessage = chatHistory.querySelector('.chat-message.assistant:last-child');
        if (lastMessage) {
            lastMessage.dataset.finalized = 'true';
        }
        
        // Re-enable send button
        const sendButton = document.getElementById('sendButton');
        sendButton.disabled = false;
        document.getElementById('sendButtonText').textContent = 'Send';
        
        // Reset current message
        this.currentMessage = null;
    }
    
    addToolLog(name, input, status) {
        const toolLog = document.getElementById('toolLog');
        const entryDiv = document.createElement('div');
        entryDiv.className = 'tool-entry';
        entryDiv.dataset.toolName = name;
        
        const timestamp = new Date().toLocaleTimeString();
        
        entryDiv.innerHTML = `
            <div class="tool-name">🔧 ${name}</div>
            <div class="tool-input">Input: ${JSON.stringify(input)}</div>
            <div class="tool-status">Status: ${status} (${timestamp})</div>
        `;
        
        toolLog.insertBefore(entryDiv, toolLog.firstChild);
    }
    
    updateToolLog(name, result) {
        const toolLog = document.getElementById('toolLog');
        const entries = toolLog.querySelectorAll('.tool-entry');
        
        // Find most recent entry with this tool name
        for (let entry of entries) {
            if (entry.dataset.toolName === name && !entry.dataset.completed) {
                const resultDiv = document.createElement('div');
                resultDiv.className = 'tool-result';
                resultDiv.textContent = `Result: ${JSON.stringify(result).substring(0, 200)}`;
                
                entry.appendChild(resultDiv);
                entry.dataset.completed = 'true';
                break;
            }
        }
    }
    
    extractMetricsFromToolResult(toolName, result) {
        // Extract blockchain metrics
        if (toolName === 'get_wallet_balance' && result.balance !== undefined) {
            document.getElementById('walletBalance').textContent = 
                `${parseFloat(result.balance).toFixed(4)} ETH`;
        }
        
        if (toolName === 'optimize_gas_fees' && result.current_gas_gwei !== undefined) {
            document.getElementById('gasPrice').textContent = 
                `${result.current_gas_gwei} Gwei`;
        }
        
        if (toolName === 'analyze_portfolio_risk' && result.sharpe_ratio !== undefined) {
            document.getElementById('riskScore').textContent = 
                result.sharpe_ratio.toFixed(2);
        }
        
        // Extract QAOA metrics
        if (toolName === 'run_cuda_q_qaoa') {
            if (result.final_energy !== undefined) {
                document.getElementById('qaoaEnergy').textContent = 
                    result.final_energy.toFixed(4);
            }
            if (result.purity !== undefined) {
                document.getElementById('qaoaPurity').textContent = 
                    result.purity.toFixed(4);
            }
            if (result.converged !== undefined) {
                document.getElementById('qaoaConvergence').textContent = 
                    result.converged ? 'Yes' : 'No';
            }
        }
    }
    
    // =========================================================================
    // 2. Real-time Live Metrics WebSocket / Polling Fallback
    // =========================================================================
    
    connectMetricsWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/live-metrics`;
        
        console.log('Connecting to metrics WebSocket...');
        this.metricsWs = new WebSocket(wsUrl);
        
        this.metricsWs.onopen = () => {
            console.log('Metrics WebSocket connected');
            this.metricsWsConnected = true;
            
            // Clear polling fallback if active
            if (this.pollingInterval) {
                clearInterval(this.pollingInterval);
                this.pollingInterval = null;
            }
        };
        
        this.metricsWs.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                if (message.type === 'metrics_update') {
                    this.handleLiveMetrics(message.data);
                }
            } catch (e) {
                console.error('Error parsing live metrics event:', e);
            }
        };
        
        this.metricsWs.onerror = (error) => {
            console.error('Metrics WebSocket error:', error);
            this.metricsWsConnected = false;
        };
        
        this.metricsWs.onclose = () => {
            console.log('Metrics WebSocket closed. Reverting to HTTP polling.');
            this.metricsWsConnected = false;
            
            // Fallback immediately to polling, then retry WS connection
            if (!this.pollingInterval) {
                this.startVRAMPolling();
            }
            
            setTimeout(() => {
                if (!this.metricsWsConnected) {
                    this.connectMetricsWebSocket();
                }
            }, 5000);
        };
    }
    
    startVRAMPolling() {
        this.updateVRAMStatus();
        this.pollingInterval = setInterval(() => {
            this.updateVRAMStatus();
        }, 2000);
    }
    
    async updateVRAMStatus() {
        try {
            const response = await fetch('/api/vram');
            if (!response.ok) throw new Error('Failed to poll VRAM status');
            
            const data = await response.json();
            this.handleLiveMetrics(data);
        } catch (error) {
            console.error('Error polling VRAM status:', error);
        }
    }
    
    handleLiveMetrics(data) {
        this.latestMetrics = data;
        
        // Update gauge chart
        const usedPercent = data.vram_percent;
        const freePercent = 100 - usedPercent;
        this.vramChart.data.datasets[0].data = [usedPercent, freePercent];
        
        // Dynamic gauge colors based on states
        let color = '#3b82f6'; // OPTIMAL
        if (data.state === 'DYNAMIC') color = '#f59e0b';
        else if (data.state === 'SEQUENTIAL') color = '#ef4444';
        else if (data.state === 'OFFLOAD') color = '#b91c1c';
        else if (data.state === 'DEGRADED') color = '#6b7280'; // Degraded status grey
        
        this.vramChart.data.datasets[0].backgroundColor = [color, '#1a2142'];
        this.vramChart.update();
        
        // Update dashboard text metrics
        const stateEl = document.getElementById('vramState');
        stateEl.textContent = data.state;
        stateEl.className = `metric-value ${data.state}`;
        
        document.getElementById('hamiltonian').textContent = data.hamiltonian.toFixed(2);
        document.getElementById('vramUsage').textContent = 
            `${data.vram_used_mib} / ${data.vram_total_mib} MB`;
        
        if (data.gpu_name) {
            document.getElementById('gpuName').textContent = data.gpu_name;
        }
        document.getElementById('gpuTemp').textContent = `${data.temperature}°C`;
        
        const powerEl = document.getElementById('gpuPower');
        if (powerEl && data.power_watts !== undefined) {
            powerEl.textContent = `${data.power_watts.toFixed(1)}W`;
        }
        
        // Update line history chart
        this.updateTrendsChart(data);
    }
    
    setupVRAMGauge() {
        const ctx = document.getElementById('vramGauge').getContext('2d');
        
        this.vramChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Used', 'Free'],
                datasets: [{
                    data: [0, 100],
                    backgroundColor: ['#3b82f6', '#1a2142'],
                    borderColor: ['#60a5fa', '#2d3748'],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.label + ': ' + context.parsed + '%';
                            }
                        }
                    }
                }
            }
        });
    }
    
    // =========================================================================
    // 3. Trends Line Chart (History plots)
    // =========================================================================
    
    setupTrendsChart() {
        const ctx = document.getElementById('trendsChart').getContext('2d');
        
        this.trendsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'VRAM Usage (%)',
                        data: [],
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        borderWidth: 2,
                        tension: 0.3,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Hamiltonian',
                        data: [],
                        borderColor: '#10b981',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        tension: 0.3,
                        yAxisID: 'y1'
                    },
                    {
                        label: 'Temp (°C)',
                        data: [],
                        borderColor: '#ef4444',
                        backgroundColor: 'transparent',
                        borderWidth: 1.5,
                        borderDash: [5, 5],
                        tension: 0.3,
                        yAxisID: 'y'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#9ca3af', font: { size: 10 } }
                    },
                    y: {
                        position: 'left',
                        min: 0,
                        max: 100,
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#9ca3af' }
                    },
                    y1: {
                        position: 'right',
                        min: 0,
                        max: 10,
                        grid: { drawOnChartArea: false },
                        ticks: { color: '#9ca3af' }
                    }
                },
                plugins: {
                    legend: {
                        labels: { color: '#e5e7eb', font: { size: 11 } }
                    }
                }
            }
        });
    }
    
    updateTrendsChart(data) {
        if (!this.trendsChart) return;
        
        const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        
        this.trendsChart.data.labels.push(timestamp);
        this.trendsChart.data.datasets[0].data.push(data.vram_percent);
        this.trendsChart.data.datasets[1].data.push(data.hamiltonian);
        this.trendsChart.data.datasets[2].data.push(data.temperature);
        
        const maxPoints = 30;
        if (this.trendsChart.data.labels.length > maxPoints) {
            this.trendsChart.data.labels.shift();
            this.trendsChart.data.datasets[0].data.shift();
            this.trendsChart.data.datasets[1].data.shift();
            this.trendsChart.data.datasets[2].data.shift();
        }
        
        this.trendsChart.update('none'); // Update without redraw animation for speed
    }
    
    // =========================================================================
    // 4. Claws Propagation Panel (Manual alerts)
    // =========================================================================
    
    setupPropagation() {
        const button = document.getElementById('propagateButton');
        const textarea = document.getElementById('propagateMessage');
        const resultDiv = document.getElementById('propagationResult');
        
        button.addEventListener('click', async () => {
            const message = textarea.value.trim();
            if (!message) {
                alert('Please enter a message to propagate.');
                return;
            }
            
            button.disabled = true;
            button.textContent = 'Propagating...';
            resultDiv.textContent = '';
            resultDiv.className = 'propagation-result';
            
            try {
                const response = await fetch('/api/propagate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        message: message,
                        metrics: this.latestMetrics || null,
                        channels: ['telegram', 'kimiclaw', 'openclaw', 'slack']
                    })
                });
                
                const data = await response.json();
                
                if (response.ok && data.status === 'success') {
                    resultDiv.textContent = `Successfully propagated to: ${data.delivered.join(', ') || 'none'}`;
                    resultDiv.className = 'propagation-result success';
                    textarea.value = '';
                } else {
                    resultDiv.textContent = `Error: ${data.detail || 'Failed to propagate'}`;
                    resultDiv.className = 'propagation-result error';
                }
            } catch (error) {
                console.error('Propagation error:', error);
                resultDiv.textContent = 'Network error during propagation.';
                resultDiv.className = 'propagation-result error';
            } finally {
                button.disabled = false;
                button.textContent = 'Propagate to Claws';
            }
        });
    }
    
    updateClawStatuses(connections) {
        const claws = ['telegram', 'kimiclaw', 'openclaw', 'slack'];
        claws.forEach(claw => {
            const element = document.querySelector(`#claw-${claw} .status-dot`);
            if (element) {
                const status = connections[claw]?.status || 'no_token';
                element.className = 'status-dot'; // Reset classes
                if (status === 'ready') {
                    element.classList.add('ready');
                } else if (status === 'no_token') {
                    element.classList.add('no_token');
                } else {
                    element.classList.add('offline');
                }
            }
        });
    }
    
    async updateAgentStateMetrics() {
        try {
            const response = await fetch('/api/agent/state');
            if (response.ok) {
                const data = await response.json();
                if (data.connections) {
                    this.updateClawStatuses(data.connections);
                }
            }
        } catch (error) {
            console.error('Error fetching agent state:', error);
        }
    }
    
    startAgentStatePolling() {
        this.updateAgentStateMetrics();
        setInterval(() => this.updateAgentStateMetrics(), 10000);
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new DiamondNodeDashboard();
});
