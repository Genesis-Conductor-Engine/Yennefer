/**
 * QFLOP Token Minter Service
 * Automatically mints QFLOP tokens based on GPU production
 * Runs every 5 minutes to batch mint accumulated production
 */

const { ethers } = require("ethers");
const fs = require("fs");
require("dotenv").config();

// Configuration
const QFLOP_TOKEN_ADDRESS = "0xa8F5e136aa74803B8DB377a14f79F6c8Dd3959c7";
const RPC_URL = "https://mainnet.base.org";
const MINT_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes
const STATE_FILE = "/dev/shm/qmcp_cuda_maxpower.json";

// Get private key from .env
const PRIVATE_KEY = process.env.BASE_PRIVATE_KEY || process.env.ETH_PRIVATE_KEY;

// Minimal ABI for minting
const QFLOP_ABI = [
    "function mintFromTime(address to) external",
    "function pendingMint() external view returns (uint256)",
    "function balanceOf(address) external view returns (uint256)",
    "function totalSupply() external view returns (uint256)",
    "function lastMintTimestamp() external view returns (uint256)"
];

class QFLOPMinter {
    constructor() {
        this.provider = new ethers.JsonRpcProvider(RPC_URL);
        
        if (!PRIVATE_KEY) {
            throw new Error("No private key found in environment");
        }
        
        this.wallet = new ethers.Wallet(PRIVATE_KEY, this.provider);
        this.token = new ethers.Contract(QFLOP_TOKEN_ADDRESS, QFLOP_ABI, this.wallet);
        
        this.totalMinted = 0n;
        this.mintCount = 0;
        this.lastGPUState = null;
    }
    
    async initialize() {
        console.log("═══════════════════════════════════════════════════════════════");
        console.log("  QFLOP TOKEN MINTER SERVICE");
        console.log("═══════════════════════════════════════════════════════════════");
        console.log("");
        console.log("Token:", QFLOP_TOKEN_ADDRESS);
        console.log("Minter:", this.wallet.address);
        
        const balance = await this.provider.getBalance(this.wallet.address);
        console.log("ETH Balance:", ethers.formatEther(balance), "ETH");
        
        const tokenBalance = await this.token.balanceOf(this.wallet.address);
        console.log("QFLOP Balance:", ethers.formatEther(tokenBalance), "QFLOP");
        
        console.log("");
        console.log("Mint interval:", MINT_INTERVAL_MS / 1000, "seconds");
        console.log("─────────────────────────────────────────────────────────────────");
    }
    
    readGPUState() {
        try {
            const data = fs.readFileSync(STATE_FILE, "utf8");
            return JSON.parse(data);
        } catch (e) {
            return null;
        }
    }
    
    async checkPendingMint() {
        try {
            const pending = await this.token.pendingMint();
            return pending;
        } catch (e) {
            console.log("Error checking pending:", e.message);
            return 0n;
        }
    }
    
    async mint() {
        try {
            // Check GPU state
            const gpuState = this.readGPUState();
            if (gpuState) {
                console.log(`📊 GPU: ${gpuState.tflops_rate?.toFixed(2) || 0} TFLOPS | $${gpuState.daily_usd?.toFixed(2) || 0}/day`);
            }
            
            // Check pending tokens
            const pending = await this.checkPendingMint();
            console.log(`⏳ Pending: ${ethers.formatEther(pending)} QFLOP`);
            
            if (pending === 0n) {
                console.log("⏸️  Nothing to mint yet");
                return;
            }
            
            // Check gas
            const balance = await this.provider.getBalance(this.wallet.address);
            const feeData = await this.provider.getFeeData();
            const estimatedGas = 100000n; // Estimate
            const gasCost = estimatedGas * feeData.gasPrice;
            
            if (balance < gasCost) {
                console.log("❌ Insufficient gas for mint");
                return;
            }
            
            // Mint
            console.log("🔨 Minting...");
            const tx = await this.token.mintFromTime(this.wallet.address, {
                gasLimit: 150000
            });
            
            console.log("TX:", tx.hash);
            const receipt = await tx.wait();
            
            if (receipt.status === 1) {
                this.mintCount++;
                this.totalMinted += pending;
                
                const newBalance = await this.token.balanceOf(this.wallet.address);
                console.log("✅ Minted! New balance:", ethers.formatEther(newBalance), "QFLOP");
                
                // Log to file
                this.logMint(pending, tx.hash);
            } else {
                console.log("❌ Mint failed");
            }
            
        } catch (e) {
            console.log("Mint error:", e.message);
        }
    }
    
    logMint(amount, txHash) {
        const log = {
            timestamp: new Date().toISOString(),
            amount: ethers.formatEther(amount),
            txHash: txHash,
            totalMinted: ethers.formatEther(this.totalMinted),
            mintCount: this.mintCount
        };
        
        fs.appendFileSync(
            "/home/yenn/logs/qflop_mints.jsonl",
            JSON.stringify(log) + "\n"
        );
    }
    
    async run() {
        await this.initialize();
        
        console.log("");
        console.log("🚀 Starting mint loop...");
        console.log("");
        
        // Initial mint
        await this.mint();
        
        // Mint loop
        setInterval(async () => {
            console.log(`\n[${new Date().toISOString()}] Mint cycle ${this.mintCount + 1}`);
            await this.mint();
        }, MINT_INTERVAL_MS);
    }
}

// Ensure log directory exists
if (!fs.existsSync("/home/yenn/logs")) {
    fs.mkdirSync("/home/yenn/logs", { recursive: true });
}

const minter = new QFLOPMinter();
minter.run().catch(console.error);
