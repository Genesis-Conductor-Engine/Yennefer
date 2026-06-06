#!/usr/bin/env node
/**
 * PROCESS GUARDIAN - Failure Analysis & Auto-Correction System
 * 
 * Monitors all Yennefer services, analyzes failures, and triggers
 * automatic corrections based on failure patterns.
 * 
 * Features:
 * - Real-time PM2 process monitoring
 * - GitHub Actions workflow failure detection
 * - Shared memory corruption detection
 * - Gas balance monitoring with auto-bridge
 * - Pattern-based failure classification
 * - Auto-restart with exponential backoff
 * - Slack/Discord webhook alerts (optional)
 */

const { execSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

// Configuration
const CONFIG = {
    POLL_INTERVAL_MS: 10000,  // 10 seconds
    MAX_RESTART_ATTEMPTS: 5,
    BACKOFF_BASE_MS: 5000,
    GITHUB_REPO: 'Genesis-Conductor-Engine/Yennefer',
    LOG_FILE: '/home/yenn/.yennefer/logs/guardian.log',
    STATE_FILE: '/dev/shm/guardian_state.json',
    
    // Thresholds
    MIN_GAS_ETH: 0.0001,
    MAX_MEMORY_MB: 500,
    MAX_CPU_PERCENT: 95,
    MAX_RESTART_RATE: 10,  // per minute
    
    // Critical services (order matters for dependencies)
    // QFLOP services included for keep-alive/auto-recovery: qflop-backfill (Base L2 revenue recovery consumer), qflop-miner, qflop-minter
    CRITICAL_SERVICES: [
        'diamond-watchdog',
        'qmcp-bridge',
        'qflop-backfill',
        'qflop-miner',
        'qflop-minter',
        'yennefer_conductor'
    ],
    
    // Shared memory files to monitor
    SHARED_MEMORY_FILES: [
        '/dev/shm/qmcp_live_stats.json',
        '/dev/shm/yennefer_soul_state.json',
        '/dev/shm/qmcp_trigger.json'
    ]
};

// Failure types
const FAILURE_TYPES = {
    PROCESS_CRASHED: 'PROCESS_CRASHED',
    PROCESS_STUCK: 'PROCESS_STUCK',
    HIGH_MEMORY: 'HIGH_MEMORY',
    HIGH_CPU: 'HIGH_CPU',
    RESTART_LOOP: 'RESTART_LOOP',
    SHARED_MEMORY_CORRUPT: 'SHARED_MEMORY_CORRUPT',
    SHARED_MEMORY_STALE: 'SHARED_MEMORY_STALE',
    LOW_GAS: 'LOW_GAS',
    GITHUB_WORKFLOW_FAILED: 'GITHUB_WORKFLOW_FAILED',
    NETWORK_ERROR: 'NETWORK_ERROR'
};

// Correction actions
const CORRECTIONS = {
    [FAILURE_TYPES.PROCESS_CRASHED]: 'restart_service',
    [FAILURE_TYPES.PROCESS_STUCK]: 'force_restart_service',
    [FAILURE_TYPES.HIGH_MEMORY]: 'restart_service',
    [FAILURE_TYPES.HIGH_CPU]: 'throttle_and_restart',
    [FAILURE_TYPES.RESTART_LOOP]: 'disable_and_alert',
    [FAILURE_TYPES.SHARED_MEMORY_CORRUPT]: 'reinitialize_shared_memory',
    [FAILURE_TYPES.SHARED_MEMORY_STALE]: 'trigger_watchdog',
    [FAILURE_TYPES.LOW_GAS]: 'dispatch_bridge_workflow',
    [FAILURE_TYPES.GITHUB_WORKFLOW_FAILED]: 'retry_workflow',
    [FAILURE_TYPES.NETWORK_ERROR]: 'wait_and_retry'
};

class ProcessGuardian {
    constructor() {
        this.state = this.loadState();
        this.running = true;
        this.ensureLogDir();
    }

    ensureLogDir() {
        const logDir = path.dirname(CONFIG.LOG_FILE);
        if (!fs.existsSync(logDir)) {
            fs.mkdirSync(logDir, { recursive: true });
        }
    }

    loadState() {
        try {
            if (fs.existsSync(CONFIG.STATE_FILE)) {
                return JSON.parse(fs.readFileSync(CONFIG.STATE_FILE, 'utf-8'));
            }
        } catch (e) {}
        return {
            restartCounts: {},
            lastRestarts: {},
            disabledServices: [],
            failures: [],
            corrections: [],
            startTime: Date.now()
        };
    }

    saveState() {
        try {
            fs.writeFileSync(CONFIG.STATE_FILE, JSON.stringify(this.state, null, 2));
        } catch (e) {
            this.log('ERROR', `Failed to save state: ${e.message}`);
        }
    }

    log(level, message) {
        const timestamp = new Date().toISOString();
        const entry = `[${timestamp}] [${level}] ${message}`;
        console.log(entry);
        try {
            fs.appendFileSync(CONFIG.LOG_FILE, entry + '\n');
        } catch (e) {}
    }

    // ==================== ANALYSIS FUNCTIONS ====================

    async analyzePM2Processes() {
        const failures = [];
        
        try {
            const result = execSync('npx pm2 jlist 2>/dev/null', { encoding: 'utf-8' });
            const processes = JSON.parse(result);
            
            for (const proc of processes) {
                const name = proc.name;
                const status = proc.pm2_env?.status;
                const memory = (proc.monit?.memory || 0) / 1024 / 1024;
                const cpu = proc.monit?.cpu || 0;
                const restarts = proc.pm2_env?.restart_time || 0;
                
                // Check if crashed
                if (status !== 'online') {
                    failures.push({
                        type: FAILURE_TYPES.PROCESS_CRASHED,
                        service: name,
                        details: { status, restarts }
                    });
                    continue;
                }
                
                // Check memory usage
                if (memory > CONFIG.MAX_MEMORY_MB) {
                    failures.push({
                        type: FAILURE_TYPES.HIGH_MEMORY,
                        service: name,
                        details: { memory: memory.toFixed(0) + 'MB' }
                    });
                }
                
                // Check CPU usage
                if (cpu > CONFIG.MAX_CPU_PERCENT) {
                    failures.push({
                        type: FAILURE_TYPES.HIGH_CPU,
                        service: name,
                        details: { cpu: cpu + '%' }
                    });
                }
                
                // Check restart loop
                const lastRestart = this.state.lastRestarts[name] || 0;
                const timeSinceRestart = Date.now() - lastRestart;
                if (timeSinceRestart < 60000 && restarts > CONFIG.MAX_RESTART_RATE) {
                    failures.push({
                        type: FAILURE_TYPES.RESTART_LOOP,
                        service: name,
                        details: { restarts, timeSinceRestart }
                    });
                }
            }
            
            // Check for missing critical services
            const runningNames = processes.map(p => p.name);
            for (const critical of CONFIG.CRITICAL_SERVICES) {
                if (!runningNames.includes(critical) && !this.state.disabledServices.includes(critical)) {
                    failures.push({
                        type: FAILURE_TYPES.PROCESS_CRASHED,
                        service: critical,
                        details: { reason: 'Service not found in PM2' }
                    });
                }
            }
            
        } catch (e) {
            this.log('ERROR', `PM2 analysis failed: ${e.message}`);
        }
        
        return failures;
    }

    async analyzeSharedMemory() {
        const failures = [];
        
        for (const file of CONFIG.SHARED_MEMORY_FILES) {
            try {
                if (!fs.existsSync(file)) {
                    failures.push({
                        type: FAILURE_TYPES.SHARED_MEMORY_CORRUPT,
                        service: 'shared_memory',
                        details: { file, reason: 'File missing' }
                    });
                    continue;
                }
                
                const stats = fs.statSync(file);
                const age = (Date.now() - stats.mtimeMs) / 1000;
                
                // Check if stale (no update in 60 seconds for trigger, 30 for others)
                const maxAge = file.includes('trigger') ? 300 : 60;
                if (age > maxAge && !file.includes('trigger')) {
                    failures.push({
                        type: FAILURE_TYPES.SHARED_MEMORY_STALE,
                        service: 'shared_memory',
                        details: { file, age: age.toFixed(0) + 's' }
                    });
                }
                
                // Try to parse JSON
                const content = fs.readFileSync(file, 'utf-8');
                JSON.parse(content);
                
            } catch (e) {
                if (e instanceof SyntaxError) {
                    failures.push({
                        type: FAILURE_TYPES.SHARED_MEMORY_CORRUPT,
                        service: 'shared_memory',
                        details: { file, reason: 'Invalid JSON' }
                    });
                }
            }
        }
        
        return failures;
    }

    async analyzeGitHubWorkflows() {
        const failures = [];
        
        try {
            const result = execSync(
                `gh run list --workflow qflop-dual-bridge.yml --repo ${CONFIG.GITHUB_REPO} --limit 5 --json databaseId,conclusion,status 2>/dev/null`,
                { encoding: 'utf-8' }
            );
            const runs = JSON.parse(result);
            
            // Check for recent failures
            for (const run of runs) {
                if (run.conclusion === 'failure') {
                    failures.push({
                        type: FAILURE_TYPES.GITHUB_WORKFLOW_FAILED,
                        service: 'github_actions',
                        details: { runId: run.databaseId }
                    });
                }
            }
            
        } catch (e) {
            // GitHub CLI not available or rate limited
        }
        
        return failures;
    }

    async analyzeGasBalance() {
        const failures = [];
        
        try {
            // Check gas balance from miner logs (qflop-miner primary; qflop-backfill now also in CRITICAL_SERVICES for full QFLOP keep-alive)
            const logs = execSync(
                'npx pm2 logs qflop-miner --lines 10 --nostream 2>&1 | grep -i "gas" | tail -1',
                { encoding: 'utf-8' }
            );
            
            const match = logs.match(/(\d+\.?\d*)\s*ETH/i);
            if (match) {
                const balance = parseFloat(match[1]);
                if (balance < CONFIG.MIN_GAS_ETH) {
                    failures.push({
                        type: FAILURE_TYPES.LOW_GAS,
                        service: 'blockchain',
                        details: { balance: balance + ' ETH', required: CONFIG.MIN_GAS_ETH + ' ETH' }
                    });
                }
            }
            
        } catch (e) {}
        
        return failures;
    }

    // ==================== CORRECTION FUNCTIONS ====================

    async applyCorrection(failure) {
        const action = CORRECTIONS[failure.type];
        this.log('INFO', `Applying correction: ${action} for ${failure.service}`);
        
        try {
            switch (action) {
                case 'restart_service':
                    await this.restartService(failure.service);
                    break;
                    
                case 'force_restart_service':
                    await this.forceRestartService(failure.service);
                    break;
                    
                case 'throttle_and_restart':
                    await this.throttleAndRestart(failure.service);
                    break;
                    
                case 'disable_and_alert':
                    await this.disableAndAlert(failure.service);
                    break;
                    
                case 'reinitialize_shared_memory':
                    await this.reinitializeSharedMemory(failure.details.file);
                    break;
                    
                case 'trigger_watchdog':
                    await this.triggerWatchdog();
                    break;
                    
                case 'dispatch_bridge_workflow':
                    await this.dispatchBridgeWorkflow();
                    break;
                    
                case 'retry_workflow':
                    await this.retryWorkflow(failure.details.runId);
                    break;
                    
                case 'wait_and_retry':
                    await this.waitAndRetry(failure.service);
                    break;
                    
                default:
                    this.log('WARN', `Unknown correction action: ${action}`);
            }
            
            this.state.corrections.push({
                timestamp: Date.now(),
                failure,
                action,
                success: true
            });
            
        } catch (e) {
            this.log('ERROR', `Correction failed: ${e.message}`);
            this.state.corrections.push({
                timestamp: Date.now(),
                failure,
                action,
                success: false,
                error: e.message
            });
        }
    }

    async restartService(service) {
        // Check restart count
        this.state.restartCounts[service] = (this.state.restartCounts[service] || 0) + 1;
        
        if (this.state.restartCounts[service] > CONFIG.MAX_RESTART_ATTEMPTS) {
            throw new Error(`Max restart attempts exceeded for ${service}`);
        }
        
        // Exponential backoff
        const backoff = CONFIG.BACKOFF_BASE_MS * Math.pow(2, this.state.restartCounts[service] - 1);
        this.log('INFO', `Restarting ${service} after ${backoff}ms backoff`);
        
        await new Promise(r => setTimeout(r, backoff));
        
        execSync(`npx pm2 restart ${service} 2>/dev/null || npx pm2 start ${service} 2>/dev/null`);
        this.state.lastRestarts[service] = Date.now();
        
        // Reset restart count after successful restart
        setTimeout(() => {
            this.state.restartCounts[service] = 0;
        }, 300000); // Reset after 5 minutes of stability
    }

    async forceRestartService(service) {
        this.log('WARN', `Force restarting ${service}`);
        execSync(`npx pm2 delete ${service} 2>/dev/null || true`);
        await new Promise(r => setTimeout(r, 2000));
        
        // Re-add based on service type
        const serviceConfigs = {
            'diamond-watchdog': 'npx pm2 start genesis-q-mem/qmcp_diamond_watchdog.py --name diamond-watchdog --interpreter python3',
            'qflop-miner': 'npx pm2 start scripts/qflop_mining_daemon.cjs --name qflop-miner',
            'qflop-backfill': 'npx pm2 start qflop-backfill/orchestrator/backfill_orchestrator.mjs --name qflop-backfill --interpreter node --interpreter-args --experimental-vm-modules',
            'qmcp-bridge': 'npx pm2 start scripts/qmcp_bridge.cjs --name qmcp-bridge'
        };
        
        if (serviceConfigs[service]) {
            execSync(`cd /home/yenn && ${serviceConfigs[service]} 2>/dev/null`);
        } else {
            execSync(`npx pm2 restart ${service} 2>/dev/null`);
        }
    }

    async throttleAndRestart(service) {
        this.log('WARN', `Throttling and restarting ${service}`);
        // Send SIGSTOP to pause, then restart
        try {
            const pid = execSync(`npx pm2 pid ${service} 2>/dev/null`, { encoding: 'utf-8' }).trim();
            if (pid) {
                execSync(`kill -STOP ${pid} 2>/dev/null || true`);
                await new Promise(r => setTimeout(r, 5000));
                execSync(`kill -CONT ${pid} 2>/dev/null || true`);
            }
        } catch (e) {}
        await this.restartService(service);
    }

    async disableAndAlert(service) {
        this.log('ERROR', `Disabling ${service} due to restart loop`);
        this.state.disabledServices.push(service);
        execSync(`npx pm2 stop ${service} 2>/dev/null || true`);
        
        // Write alert to shared memory for other systems to pick up
        const alert = {
            type: 'SERVICE_DISABLED',
            service,
            timestamp: Date.now(),
            reason: 'Restart loop detected'
        };
        fs.writeFileSync('/dev/shm/guardian_alert.json', JSON.stringify(alert, null, 2));
    }

    async reinitializeSharedMemory(file) {
        this.log('INFO', `Reinitializing shared memory: ${file}`);
        
        const defaults = {
            '/dev/shm/qmcp_live_stats.json': { status: 'INITIALIZED', timestamp: Date.now() },
            '/dev/shm/yennefer_soul_state.json': { breath: 0, coherence: 1.0, timestamp: Date.now() },
            '/dev/shm/qmcp_trigger.json': { status: 'READY' }
        };
        
        const defaultContent = defaults[file] || { initialized: Date.now() };
        fs.writeFileSync(file, JSON.stringify(defaultContent, null, 2));
    }

    async triggerWatchdog() {
        this.log('INFO', 'Triggering watchdog refresh');
        const trigger = {
            branch_id: `GUARDIAN_${Date.now()}`,
            job_type: 'SEISMIC_SHAKE',
            parameters: { noise_precision: 0.1 }
        };
        fs.writeFileSync('/dev/shm/qmcp_trigger.json', JSON.stringify(trigger));
    }

    async dispatchBridgeWorkflow() {
        this.log('INFO', 'Dispatching ETH bridge workflow for gas');
        try {
            execSync(
                `gh workflow run qflop-dual-bridge.yml --repo ${CONFIG.GITHUB_REPO} -f duration_minutes=5 -f power_mode=maxpower 2>/dev/null`
            );
        } catch (e) {
            this.log('WARN', 'Failed to dispatch bridge workflow');
        }
    }

    async retryWorkflow(runId) {
        this.log('INFO', `Retrying failed workflow: ${runId}`);
        try {
            execSync(`gh run rerun ${runId} --repo ${CONFIG.GITHUB_REPO} 2>/dev/null`);
        } catch (e) {
            this.log('WARN', `Failed to retry workflow ${runId}`);
        }
    }

    async waitAndRetry(service) {
        this.log('INFO', `Waiting before retry for ${service}`);
        await new Promise(r => setTimeout(r, 30000));
        await this.restartService(service);
    }

    // ==================== MAIN LOOP ====================

    async runAnalysis() {
        const allFailures = [];
        
        // Run all analyzers
        const [pm2Failures, shmFailures, ghFailures, gasFailures] = await Promise.all([
            this.analyzePM2Processes(),
            this.analyzeSharedMemory(),
            this.analyzeGitHubWorkflows(),
            this.analyzeGasBalance()
        ]);
        
        allFailures.push(...pm2Failures, ...shmFailures, ...ghFailures, ...gasFailures);
        
        return allFailures;
    }

    async run() {
        console.log('');
        console.log('╔═══════════════════════════════════════════════════════════════╗');
        console.log('║         🛡️  PROCESS GUARDIAN - ACTIVE 🛡️                      ║');
        console.log('╚═══════════════════════════════════════════════════════════════╝');
        console.log(`   Poll Interval: ${CONFIG.POLL_INTERVAL_MS / 1000}s`);
        console.log(`   Max Restarts:  ${CONFIG.MAX_RESTART_ATTEMPTS}`);
        console.log(`   Log File:      ${CONFIG.LOG_FILE}`);
        console.log('');
        
        while (this.running) {
            try {
                const failures = await this.runAnalysis();
                
                if (failures.length > 0) {
                    this.log('WARN', `Detected ${failures.length} failure(s)`);
                    
                    for (const failure of failures) {
                        this.log('INFO', `  - ${failure.type}: ${failure.service} (${JSON.stringify(failure.details)})`);
                        this.state.failures.push({ ...failure, timestamp: Date.now() });
                        
                        // Apply correction
                        await this.applyCorrection(failure);
                    }
                }
                
                // Trim old entries
                const oneHourAgo = Date.now() - 3600000;
                this.state.failures = this.state.failures.filter(f => f.timestamp > oneHourAgo);
                this.state.corrections = this.state.corrections.filter(c => c.timestamp > oneHourAgo);
                
                this.saveState();
                
            } catch (e) {
                this.log('ERROR', `Guardian loop error: ${e.message}`);
            }
            
            await new Promise(r => setTimeout(r, CONFIG.POLL_INTERVAL_MS));
        }
    }
}

// Start guardian
const guardian = new ProcessGuardian();
guardian.run().catch(console.error);
