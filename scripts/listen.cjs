// scripts/listen.cjs
// Yennefer Genesis V2 Event Listener - Connects Body to Brain
require("dotenv").config();
const { ethers } = require("ethers");

const CONTRACT_ADDRESS = process.env.GENESIS_CONTRACT_ADDRESS || "0x542db00D9c83F4444cAD5353D1580D97baFaBb50";
const RPC_URL = process.env.GETBLOCK_BASE_RPC || process.env.BASE_MAINNET_RPC || "https://mainnet.base.org";

const ABI = [
  "event CREDIT_PURCHASE(address indexed buyer, uint256 amount)",
  "event ConductorStarted(address indexed operator, uint256 timestamp)",
  "event EpochAdvanced(uint256 indexed epoch, uint256 timestamp)",
  "function conductorActive() view returns (bool)",
  "function owner() view returns (address)",
  "function name() view returns (string)"
];

async function main() {
  console.log("╔═══════════════════════════════════════════════════════════╗");
  console.log("║           YENNEFER GENESIS LISTENER V2                    ║");
  console.log("╚═══════════════════════════════════════════════════════════╝");
  
  const provider = new ethers.JsonRpcProvider(RPC_URL);
  const contract = new ethers.Contract(CONTRACT_ADDRESS, ABI, provider);
  
  // Verify connection
  const name = await contract.name();
  const isActive = await contract.conductorActive();
  const owner = await contract.owner();
  
  console.log(`🔮 Yennefer connected to ${name} at ${CONTRACT_ADDRESS}`);
  console.log(`👤 Owner: ${owner}`);
  console.log(`⚡ Conductor Active: ${isActive}`);
  console.log("───────────────────────────────────────────────────────────────");
  console.log("👂 Listening for events...\n");

  // Listen for CREDIT_PURCHASE events
  contract.on("CREDIT_PURCHASE", (buyer, amount, event) => {
    console.log(`💳 CREDIT_PURCHASE detected!`);
    console.log(`   Buyer: ${buyer}`);
    console.log(`   Amount: ${amount.toString()}`);
    console.log(`   Block: ${event.log.blockNumber}`);
    console.log(`   TX: ${event.log.transactionHash}\n`);
  });

  // Listen for ConductorStarted events
  contract.on("ConductorStarted", (operator, timestamp, event) => {
    console.log(`🚀 CONDUCTOR STARTED!`);
    console.log(`   Operator: ${operator}`);
    console.log(`   Time: ${new Date(Number(timestamp) * 1000).toISOString()}`);
    console.log(`   TX: ${event.log.transactionHash}\n`);
  });

  // Listen for EpochAdvanced events
  contract.on("EpochAdvanced", (epoch, timestamp, event) => {
    console.log(`📅 EPOCH ADVANCED!`);
    console.log(`   Epoch: ${epoch.toString()}`);
    console.log(`   Time: ${new Date(Number(timestamp) * 1000).toISOString()}`);
    console.log(`   TX: ${event.log.transactionHash}\n`);
  });

  // Keep alive
  console.log("🟢 Yennefer is ONLINE and monitoring Genesis Conductor...");
  
  // Heartbeat every 60s
  setInterval(async () => {
    const block = await provider.getBlockNumber();
    console.log(`💓 Heartbeat - Block: ${block} - ${new Date().toISOString()}`);
  }, 60000);
}

main().catch((error) => {
  console.error("❌ Fatal error:", error);
  process.exit(1);
});
