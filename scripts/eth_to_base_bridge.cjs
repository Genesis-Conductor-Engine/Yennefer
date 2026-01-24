const { ethers } = require('ethers');
const http = require('http');
const fs = require('fs');

// Configuration
const LEGACY_WALLET = '0x9545e2439c5c75d3aA723AcaC1AA6B0fa1DB6956';
const MPCVAULT = '0x029472221aBa41446821777136eB82Ad171D04e6';
const PRIVATE_KEY = process.env.ETH_PRIVATE_KEY;

// RPC endpoints
const ETH_RPC = 'https://eth.llamarpc.com';
const BASE_RPC = 'https://mainnet.base.org';

// Across Protocol Bridge Contract (for auto-bridging)
const ACROSS_SPOKE_POOL_ETH = '0x5c7BCd6E7De5423a257D81B442095A1a6ced35C5';

// Bridge ABI (deposit function)
const BRIDGE_ABI = [
    'function deposit(address recipient, address originToken, uint256 amount, uint256 destinationChainId, int64 relayerFeePct, uint32 quoteTimestamp, bytes message, uint256 maxCount) payable'
];

let ethProvider, baseProvider, wallet;

async function init() {
    console.log('🔄 Initializing ETH → Base Auto-Bridge...');
    
    ethProvider = new ethers.JsonRpcProvider(ETH_RPC);
    baseProvider = new ethers.JsonRpcProvider(BASE_RPC);
    
    if (PRIVATE_KEY) {
        wallet = new ethers.Wallet(PRIVATE_KEY, ethProvider);
        console.log('✅ Wallet connected:', wallet.address);
    }
    
    // Check current balances
    await checkBalances();
}

async function checkBalances() {
    try {
        const ethBal = await ethProvider.getBalance(LEGACY_WALLET);
        const baseBal = await baseProvider.getBalance(LEGACY_WALLET);
        
        console.log('');
        console.log('═══════════════════════════════════════════════════');
        console.log('CURRENT BALANCES:');
        console.log('ETH Mainnet:  ' + ethers.formatEther(ethBal) + ' ETH');
        console.log('Base Mainnet: ' + ethers.formatEther(baseBal) + ' ETH');
        console.log('═══════════════════════════════════════════════════');
        
        return { eth: ethBal, base: baseBal };
    } catch (e) {
        console.log('Balance check error:', e.message);
        return { eth: 0n, base: 0n };
    }
}

async function bridgeToBase(amount) {
    if (!wallet) {
        console.log('❌ No wallet configured for bridging');
        return null;
    }
    
    console.log(`🌉 Bridging ${ethers.formatEther(amount)} ETH to Base...`);
    
    const bridge = new ethers.Contract(ACROSS_SPOKE_POOL_ETH, BRIDGE_ABI, wallet);
    
    // Bridge parameters
    const recipient = LEGACY_WALLET;
    const originToken = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'; // WETH
    const destinationChainId = 8453; // Base
    const relayerFeePct = 100000n; // 0.01% fee
    const quoteTimestamp = Math.floor(Date.now() / 1000);
    const message = '0x';
    const maxCount = ethers.MaxUint256;
    
    try {
        const tx = await bridge.deposit(
            recipient,
            originToken,
            amount,
            destinationChainId,
            relayerFeePct,
            quoteTimestamp,
            message,
            maxCount,
            { value: amount }
        );
        
        console.log('📤 Bridge TX sent:', tx.hash);
        const receipt = await tx.wait();
        console.log('✅ Bridge confirmed! Block:', receipt.blockNumber);
        
        return tx.hash;
    } catch (e) {
        console.log('❌ Bridge error:', e.message);
        return null;
    }
}

// Watch for incoming transactions on ETH mainnet
async function watchIncoming() {
    console.log('👀 Watching for incoming ETH transactions...');
    
    ethProvider.on('block', async (blockNumber) => {
        try {
            const block = await ethProvider.getBlock(blockNumber, true);
            if (!block || !block.prefetchedTransactions) return;
            
            for (const tx of block.prefetchedTransactions) {
                if (tx.to?.toLowerCase() === LEGACY_WALLET.toLowerCase() ||
                    tx.to?.toLowerCase() === MPCVAULT.toLowerCase()) {
                    
                    console.log('');
                    console.log('💰 INCOMING TX DETECTED!');
                    console.log('From:', tx.from);
                    console.log('To:', tx.to);
                    console.log('Amount:', ethers.formatEther(tx.value), 'ETH');
                    console.log('Hash:', tx.hash);
                    
                    // Log to file
                    fs.appendFileSync('/home/yenn/logs/eth_incoming.log', 
                        `${new Date().toISOString()} | ${tx.hash} | ${ethers.formatEther(tx.value)} ETH\n`
                    );
                    
                    // Check if we should auto-bridge
                    const balances = await checkBalances();
                    if (balances.eth > ethers.parseEther('0.001')) {
                        console.log('🚀 Auto-bridging to Base...');
                        // Keep some for gas
                        const toBridge = balances.eth - ethers.parseEther('0.0005');
                        await bridgeToBase(toBridge);
                    }
                }
            }
        } catch (e) {
            // Ignore block fetch errors
        }
    });
}

// Webhook server
const server = http.createServer((req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    
    if (req.url === '/health') {
        res.writeHead(200);
        res.end(JSON.stringify({ status: 'ok', service: 'eth-bridge' }));
    }
    else if (req.url === '/balances') {
        checkBalances().then(b => {
            res.writeHead(200);
            res.end(JSON.stringify({
                eth_mainnet: ethers.formatEther(b.eth),
                base_mainnet: ethers.formatEther(b.base)
            }));
        });
    }
    else if (req.url === '/bridge' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', async () => {
            const { amount } = JSON.parse(body || '{}');
            const result = await bridgeToBase(ethers.parseEther(amount || '0.001'));
            res.writeHead(200);
            res.end(JSON.stringify({ txHash: result }));
        });
    }
    else {
        res.writeHead(200);
        res.end(JSON.stringify({
            endpoints: ['/health', '/balances', '/bridge'],
            wallets: { legacy: LEGACY_WALLET, mpcvault: MPCVAULT }
        }));
    }
});

const PORT = 8005;
server.listen(PORT, () => {
    console.log(`🌐 Webhook server on port ${PORT}`);
    console.log('');
    console.log('Endpoints:');
    console.log('  GET  /health   - Health check');
    console.log('  GET  /balances - Check ETH & Base balances');
    console.log('  POST /bridge   - Trigger manual bridge');
});

// Start
init().then(() => watchIncoming());
