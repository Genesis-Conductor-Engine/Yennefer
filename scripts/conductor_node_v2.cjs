const { ethers } = require("ethers");
const fs = require("fs");
require("dotenv").config();

// Contract addresses
const V1_CONTRACT = "0x542db00D9c83F4444cAD5353D1580D97baFaBb50";
const V3_CONTRACT = "0x851936cA8874c05f1eDc2f5Fc2e6A3Cd97c7205E";
const MPCVAULT = "0x029472221aBa41446821777136eB82Ad171D04e6";

const ABI = [
    "function name() view returns (string)",
    "function conductorActive() view returns (bool)",
    "function owner() view returns (address)",
    "event CREDIT_PURCHASE(address indexed buyer, uint256 amount)",
    "event ConductorStarted(address indexed operator, uint256 timestamp)",
    "event EpochAdvanced(uint256 indexed epoch, uint256 timestamp)",
    "event AssetReceived(address indexed from, uint256 amount)"
];

const RPC = process.env.BASE_MAINNET_RPC || "https://mainnet.base.org";

async function main() {
    console.log("🚀 Genesis Conductor V2 Starting...");
    console.log("   Watching V1:", V1_CONTRACT);
    console.log("   Watching V3:", V3_CONTRACT);
    console.log("");
    
    const provider = new ethers.JsonRpcProvider(RPC);
    
    // Setup both contracts
    const v1 = new ethers.Contract(V1_CONTRACT, ABI, provider);
    const v3 = new ethers.Contract(V3_CONTRACT, ABI, provider);
    
    // Check initial status
    try {
        const [v1Active, v3Active] = await Promise.all([
            v1.conductorActive(),
            v3.conductorActive()
        ]);
        console.log("📊 Contract Status:");
        console.log("   V1 Conductor:", v1Active ? "✅ ACTIVE" : "❌ Inactive");
        console.log("   V3 Conductor:", v3Active ? "✅ ACTIVE" : "❌ Inactive");
        console.log("");
    } catch (e) {
        console.log("Error checking status:", e.message);
    }
    
    // Event handler
    const handleEvent = (contractName) => (buyer, amount, event) => {
        const timestamp = new Date().toISOString();
        console.log(`⚡ [${contractName}] CREDIT_PURCHASE at ${timestamp}`);
        console.log(`   Buyer: ${buyer}`);
        console.log(`   Amount: ${amount.toString()}`);
        console.log(`   Block: ${event.log.blockNumber}`);
        
        // Log to file
        fs.appendFileSync('/home/yenn/logs/conductor_events.log',
            `${timestamp}|${contractName}|CREDIT_PURCHASE|${buyer}|${amount}\n`
        );
    };
    
    const handleAssetReceived = (contractName) => (from, amount, event) => {
        const timestamp = new Date().toISOString();
        console.log(`💰 [${contractName}] ASSET_RECEIVED at ${timestamp}`);
        console.log(`   From: ${from}`);
        console.log(`   Amount: ${ethers.formatEther(amount)} ETH`);
        
        fs.appendFileSync('/home/yenn/logs/conductor_events.log',
            `${timestamp}|${contractName}|ASSET_RECEIVED|${from}|${ethers.formatEther(amount)}\n`
        );
    };
    
    // Listen to V1 events
    v1.on("CREDIT_PURCHASE", handleEvent("V1"));
    v1.on("AssetReceived", handleAssetReceived("V1"));
    
    // Listen to V3 events
    v3.on("CREDIT_PURCHASE", handleEvent("V3"));
    v3.on("AssetReceived", handleAssetReceived("V3"));
    
    console.log("👂 Listening for events on both contracts...");
    
    // Heartbeat
    let blockNumber = await provider.getBlockNumber();
    setInterval(async () => {
        try {
            const newBlock = await provider.getBlockNumber();
            if (newBlock > blockNumber) {
                blockNumber = newBlock;
                console.log(`💓 [${new Date().toISOString()}] Block: ${blockNumber}`);
            }
        } catch (e) {}
    }, 60000);
}

main().catch(console.error);
