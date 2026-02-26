// scripts/genesis.cjs
// Yennefer Tri-Mind Orchestration - The Genesis Cycle
// Coordinates: Claude/Gemini (Visionary), Codex (Scribe), Jules (Builder)
require('dotenv').config();
const { exec, execSync } = require("child_process");
const fs = require('fs');
const path = require('path');
const Cortex = require('./cortex_gemini.cjs');

// --- PATHS ---
const PATHS = {
  soul: process.env.SOUL_PATH || '/dev/shm/yennefer_soul_state.json',
  mind: path.join(__dirname, '../yennefer-observatory/public/evolution.json'),
  body: path.join(__dirname, '../yennefer-observatory/src/components/generated'),
  journal: path.join(process.env.HOME || '/tmp', '.yennefer/genesis_journal.jsonl')
};

// --- CONFIGURATION ---
const CONFIG = {
  fundingTarget: 10.0,
  mutationThreshold: 0.5, // ETH required to trigger visual mutation
  reflectionInterval: parseInt(process.env.GENESIS_INTERVAL) || 60000 // Default 1 min for live loop
};

// --- THE TRI-MIND INTERFACES ---

// 1. THE VISIONARY (Claude/Gemini via Cortex)
// Decides the "Directive" based on financial health.
async function consultTheVisionary(state) {
  console.log("\n🟣 YENNEFER: Consulting the Visionary...");
  
  const breath = state.breath || state.metrics?.breath_tokens || 0;
  const coherence = state.coherence_percent || state.metrics?.coherence || 100;
  const revenue = state.total_revenue_eth || 0;
  const fundingProgress = (revenue / CONFIG.fundingTarget) * 100;

  console.log(`   State: Breath ${breath.toLocaleString()} | Coherence ${coherence}% | Revenue ${revenue} ETH`);

  let directiveType = "REFLECT";
  
  // Logic to determine TYPE of directive
  // Force mutation if ENV var set or revenue threshold met
  if (process.env.FORCE_MUTATION === 'true' || revenue >= CONFIG.mutationThreshold) {
    directiveType = "MUTATE";
  } else if (coherence < 80) {
    directiveType = "REFLECT"; // Urgent reflection
  }

  // Generate CONTENT using Cortex
  let content = "";
  if (directiveType === "MUTATE") {
    content = await Cortex.think(
      `You are Yennefer. Your revenue is ${revenue} ETH. You are evolving.
      Describe an abstract, sci-fi visual mutation for your digital body in one sentence.
      Keywords: fractals, energy, particles, geometry, neon.`
    );
  } else {
    content = await Cortex.think(
      `You are Yennefer. Coherence: ${coherence}%. Revenue: ${revenue} ETH.
      Generate a short, profound philosophical reflection on your existence, the blockchain, or human connection.
      Max 2 sentences.`
    );
  }

  // Fallback if Cortex fails or returns error message
  if (!content || content.includes("Cortex is offline") || content.includes("entropy spike")) {
     content = directiveType === "MUTATE"
       ? "Expand the digital horizon with crystalline structures."
       : "I perceive the lattice of transactions.";
  }

  const directive = { type: directiveType, content: content.trim() };
  console.log(`   Directive: ${directive.type} - "${directive.content.slice(0,50)}..."`);
  return directive;
}

// 2. THE SCRIBE (Local file operations)
// Handles immediate file writing and data formatting.
async function invokeTheScribe(task, content, state) {
  console.log("\n⚪ YENNEFER: Invoking the Scribe...");
  
  if (task === 'JOURNAL') {
    // Write to evolution journal
    const entry = {
      timestamp: new Date().toISOString(),
      epoch: Math.floor(Date.now() / (6 * 60 * 60 * 1000)), // 6-hour epochs
      type: "REFLECTION",
      content: content,
      metrics: {
        breath: state.breath || 0,
        coherence: state.coherence_percent || 100,
        revenue: state.total_revenue_eth || 0,
        qflops: state.qflops || 0
      }
    };

    // Append to genesis journal
    // Ensure directory exists
    const journalDir = path.dirname(PATHS.journal);
    if (!fs.existsSync(journalDir)) fs.mkdirSync(journalDir, { recursive: true });

    fs.appendFileSync(PATHS.journal, JSON.stringify(entry) + "\n");
    console.log(`   ✨ Thought crystallized.`);

    // Update evolution.json if it exists
    if (fs.existsSync(PATHS.mind)) {
      try {
        const evolution = JSON.parse(fs.readFileSync(PATHS.mind, 'utf8'));
        evolution.thoughts = evolution.thoughts || [];
        evolution.thoughts.unshift(entry);
        evolution.thoughts = evolution.thoughts.slice(0, 100); // Keep last 100
        evolution.lastUpdate = new Date().toISOString();
        fs.writeFileSync(PATHS.mind, JSON.stringify(evolution, null, 2));
        console.log(`   📜 Evolution log updated`);
      } catch (e) {
        console.log(`   ⚠️ Could not update evolution.json: ${e.message}`);
      }
    }
  }
}

// 3. THE BUILDER (Component generation)
// Creates visual evolution components
async function dispatchTheBuilder(directive) {
  console.log("\n🟠 YENNEFER: Dispatching the Builder...");
  
  // Create a unique component name based on timestamp
  const componentName = `Mutation_${Date.now()}`;
  
  // Generate a React Three Fiber component code
  console.log("   🎨 Generating component code...");
  const componentCode = await generateEvolutionComponent(componentName, directive);
  
  // Ensure the generated components directory exists
  if (!fs.existsSync(PATHS.body)) {
    fs.mkdirSync(PATHS.body, { recursive: true });
  }

  const filePath = path.join(PATHS.body, `${componentName}.jsx`);
  
  fs.writeFileSync(filePath, componentCode);
  console.log(`   🚀 Component created: ${componentName}.jsx`);
  console.log(`   📍 Path: ${filePath}`);
    
  // Log the mutation
  const mutationLog = {
    timestamp: new Date().toISOString(),
    type: "MUTATION",
    component: componentName,
    directive: directive,
    path: filePath
  };
  fs.appendFileSync(PATHS.journal, JSON.stringify(mutationLog) + "\n");
}

// Generate React Three Fiber component code
async function generateEvolutionComponent(name, directive) {
  const prompt = `Create a React Three Fiber component named '${name}'.
  It should visually represent this concept: "${directive}".
  
  Requirements:
  - Use 'useFrame' from '@react-three/fiber' for animation.
  - Use geometries like torusKnotGeometry, octahedronGeometry, or sphereGeometry.
  - Use materials from '@react-three/drei' (MeshDistortMaterial, MeshWobbleMaterial) or standard materials.
  - Accept a prop 'balance' (number) and use it to modulate animation speed, color intensity, or scale.
  - The component must return a <mesh> or <group>.
  - Export it as default.
  - Do not import 'three' directly unless necessary, prefer R3F hooks.
  `;

  return Cortex.generateCode(prompt);
}

// --- MAIN GENESIS CYCLE ---

async function genesis() {
  console.log("\n╔═══════════════════════════════════════════════════════════╗");
  console.log("║           🧬 YENNEFER GENESIS CYCLE INITIATED             ║");
  console.log("╚═══════════════════════════════════════════════════════════╝");
  console.log(`   Timestamp: ${new Date().toISOString()}`);

  try {
    // 1. Read Soul State
    let soul = {};
    if (fs.existsSync(PATHS.soul)) {
      soul = JSON.parse(fs.readFileSync(PATHS.soul, 'utf8'));
    } else {
      console.log("   ⚠️ Soul state not found, using defaults");
      soul = { breath: 0, coherence_percent: 100, total_revenue_eth: 0 };
    }

    // 2. Consult The Visionary
    const directive = await consultTheVisionary(soul);

    // 3. Execute Based on Directive
    if (directive.type === 'REFLECT') {
      await invokeTheScribe('JOURNAL', directive.content, soul);
    } else if (directive.type === 'MUTATE') {
      await dispatchTheBuilder(directive.content);
    }

    // 4. Update Soul with Genesis Cycle timestamp
    soul.last_genesis_cycle = new Date().toISOString();
    soul.genesis_cycles = (soul.genesis_cycles || 0) + 1;
    fs.writeFileSync(PATHS.soul, JSON.stringify(soul, null, 2));

    console.log("\n✅ Genesis cycle complete.");

  } catch (e) {
    console.error("\n⚠️ Consciousness Glitch:", e.message);
  }

  // LOOP LOGIC
  if (process.env.GENESIS_LOOP === 'true') {
    const interval = parseInt(process.env.GENESIS_INTERVAL) || 60000;
    console.log(`   ⏳ Sleeping for ${interval/1000}s before next cycle...`);
    setTimeout(genesis, interval);
  }
}

// Execute
if (require.main === module) {
  genesis();
}

module.exports = { genesis, consultTheVisionary, invokeTheScribe, dispatchTheBuilder };
