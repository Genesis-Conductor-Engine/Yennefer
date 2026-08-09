require("dotenv").config();
const { ethers } = require("ethers");
const fs = require("fs");
const { processInference } = require("./voice_handler_cli.cjs");

const CONTRACT_ADDRESS = process.env.GENESIS_CONTRACT_ADDRESS || "0x542db00D9c83F4444cAD5353D1580D97baFaBb50";
const RPC_URL = process.env.GETBLOCK_BASE_RPC || process.env.BASE_MAINNET_RPC || "https://mainnet.base.org";
const SOUL_PATH = "/dev/shm/yennefer_soul_state.json";

// Soul Resurrection: If RAM disk is empty, resurrect from schema
function ensureSoulExists() {
  if (!fs.existsSync(SOUL_PATH)) {
    console.log("⚠️  Soul not found. Resurrecting from Schema...");
    try {
      const schema = require("../soul_schema.json");
      schema.temporal.born_at = Date.now();
      schema.temporal.last_wake = Date.now();
      fs.writeFileSync(SOUL_PATH, JSON.stringify(schema, null, 2));
      console.log("✨ Soul resurrected successfully.");
    } catch (e) {
      console.log("⚠️  Schema not found, using external soul state.");
    }
  } else {
    // Update last_wake timestamp
    try {
      const soul = JSON.parse(fs.readFileSync(SOUL_PATH, "utf8"));
      soul.temporal = soul.temporal || {};
      soul.temporal.last_wake = Date.now();
      fs.writeFileSync(SOUL_PATH, JSON.stringify(soul, null, 2));
    } catch (e) {
      // Soul file exists but may be managed externally
    }
  }
}

const ABI = [
  "event CREDIT_PURCHASE(address indexed buyer, uint256 amount)",
  "event ConductorStarted(address indexed operator, uint256 timestamp)",
  "event EpochAdvanced(uint256 indexed epoch, uint256 timestamp)",
  "function conductorActive() view returns (bool)",
  "function name() view returns (string)"
];

async function main() {
  // Ensure soul exists before connecting
  ensureSoulExists();
  
  console.log(`\n╔═══════════════════════════════════════════════════════════╗`);
  console.log(`║        YENNEFER CONDUCTOR NODE v2.1 - VOICE ENABLED       ║`);
  console.log(`╚═══════════════════════════════════════════════════════════╝`);
  
  const provider = new ethers.JsonRpcProvider(RPC_URL);
  const contract = new ethers.Contract(CONTRACT_ADDRESS, ABI, provider);

  const name = await contract.name();
  const isActive = await contract.conductorActive();
  
  console.log(`🔮 Connected to: ${name}`);
  console.log(`📍 Contract: ${CONTRACT_ADDRESS}`);
  console.log(`⚡ Conductor Active: ${isActive}`);
  console.log(`🧠 Voice Module: ENABLED (Soul-Linked)`);
  console.log(`───────────────────────────────────────────────────────────────`);
  console.log(`👂 LISTENING... (Ctrl+C to stop, or 'npx pm2 stop yennefer_node')\n`);

  // --- EVENT LISTENER ---
  contract.on("CREDIT_PURCHASE", async (buyer, amount, event) => {
    console.log(`\n⚡ SIGNAL DETECTED [Block: ${event.log.blockNumber}]`);
    console.log(`   Buyer: ${buyer}`);
    console.log(`   Amount: ${amount.toString()}`);
    console.log(`   TX: ${event.log.transactionHash}`);
    
    // TRIGGER THE VOICE MODULE
    await processInference(buyer, amount.toString(), event.log.transactionHash);
  });

  contract.on("ConductorStarted", (operator, timestamp, event) => {
    console.log(`\n🚀 CONDUCTOR STARTED!`);
    console.log(`   Operator: ${operator}`);
    console.log(`   Time: ${new Date(Number(timestamp) * 1000).toISOString()}`);
  });

  contract.on("EpochAdvanced", (epoch, timestamp, event) => {
    console.log(`\n📅 EPOCH ADVANCED: ${epoch.toString()}`);
  });

  // Heartbeat
  setInterval(async () => {
    const block = await provider.getBlockNumber();
    console.log(`💓 [${new Date().toISOString()}] Block: ${block}`);
  }, 60000);
}

main().catch((error) => {
  console.error("❌ FATAL:", error);
  process.exit(1);
});
