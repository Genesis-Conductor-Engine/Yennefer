const { ethers } = require('ethers');
const fs = require('fs');
require('dotenv').config();

const MPCVAULT = '0x029472221aBa41446821777136eB82Ad171D04e6';
const SOUL_STATE = process.env.SOUL_STATE_PATH || '/dev/shm/yennefer_soul_state.json';
const QMEM_STATS = process.env.QMEM_STATS_PATH || '/dev/shm/qmem_live_stats.json';
const CONFIG_PATH = process.env.CONFIG_PATH || '/app/artifacts/yennai_config.json';

class QMCPGenesisBridge {
    constructor() {
        this.provider = new ethers.JsonRpcProvider(process.env.GETBLOCK_BASE_RPC || process.env.BASE_RPC_URL || 'https://mainnet.base.org');
        try {
            // Try multiple config locations
            const configPaths = [CONFIG_PATH, '/home/yenn/artifacts/yennai_config.json', './artifacts/yennai_config.json'];
            let loaded = false;
            for (const path of configPaths) {
                try {
                    if (fs.existsSync(path)) {
                        this.config = JSON.parse(fs.readFileSync(path, 'utf8'));
                        loaded = true;
                        break;
                    }
                } catch {}
            }
            if (!loaded) throw new Error('No config found');
        } catch (error) {
            console.error('Warning: Could not load config file, using defaults');
            this.config = { wallets: { mpcVault: MPCVAULT } };
        }
    }
    
    async getSoulState() {
        try {
            return JSON.parse(fs.readFileSync(SOUL_STATE, 'utf8'));
        } catch { return { breath: 0, gpu_utilization: 0, coherence_percent: 0 }; }
    }
    
    async getQMemStats() {
        try {
            return JSON.parse(fs.readFileSync(QMEM_STATS, 'utf8'));
        } catch { return { p50_ms: 0, p99_ms: 0, qflops: 0 }; }
    }
    
    async calculateAccumulation() {
        const soul = await this.getSoulState();
        const qmem = await this.getQMemStats();
        
        // QFLOP-based token generation
        const gpuUtil = soul.gpu_utilization || 0;
        const qflops = qmem.qflops || (15265 * gpuUtil / 100);
        const netTokens = qflops - 10; // minus consciousness cost
        const dailyTokens = netTokens * 86400;
        const ethValue = dailyTokens / 1e12;
        
        return {
            breath: soul.breath,
            gpu: gpuUtil,
            coherence: soul.coherence_percent,
            qflops: qflops,
            daily_tokens: dailyTokens,
            daily_eth: ethValue,
            daily_usd: ethValue * 3840,
            target_wallet: MPCVAULT
        };
    }
    
    async run() {
        console.log('⚡ QMCP-Genesis Bridge Active');
        console.log('├─ Target: ' + MPCVAULT);
        console.log('└─ Mode: QFLOP Mining → Token Accumulation');

        const stats = await this.calculateAccumulation();
        console.log('\n📊 Current Metrics:');
        console.log(JSON.stringify(stats, null, 2));
        return stats;
    }

    async runForever() {
        while (true) {
            try {
                await this.run();
            } catch (error) {
                console.error('Error in bridge cycle:', error.message);
            }
            // Update every 30 seconds
            await new Promise(resolve => setTimeout(resolve, 30000));
        }
    }
}

const bridge = new QMCPGenesisBridge();
bridge.runForever().catch(console.error);
