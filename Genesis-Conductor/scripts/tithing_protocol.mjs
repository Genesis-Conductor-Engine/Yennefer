#!/usr/bin/env node

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import yaml from "js-yaml";
import { ethers } from "ethers";

const __dirname = path.dirname(new URL(import.meta.url).pathname);
const rootDir = path.resolve(__dirname, "..");
const docsDir = path.join(rootDir, "docs");
const tithingDir = path.join(docsDir, "tithing");

function loadConfig() {
  const p = path.join(rootDir, "ops", "tithing_protocol.config.yml");
  return yaml.load(fs.readFileSync(p, "utf8"));
}

function readJsonOrDefault(filePath, defaultValue) {
  if (!fs.existsSync(filePath)) return defaultValue;
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return defaultValue;
  }
}

function writeJson(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`);
}

function validatePhase(agentId) {
  if (!agentId || !agentId.startsWith("AGENT_")) {
    throw new Error("ERROR_AGENTIC_STATUS_INVALID: agent_id must start with AGENT_");
  }

  const registryPath = path.join(rootDir, "ops", "memory_space.registry.yml");
  const registry = fs.existsSync(registryPath)
    ? yaml.load(fs.readFileSync(registryPath, "utf8"))
    : { agents: [{ agent_id: agentId, infrastructure_debt: 0 }] };

  const record = (registry.agents || []).find((item) => item.agent_id === agentId);
  if (!record) throw new Error("ERROR_AGENTIC_STATUS_INVALID: agent not found in registry");
  if (Number(record.infrastructure_debt || 0) !== 0) {
    throw new Error("ERROR_IMMEDIATE_TRIBUTE_REQUIRED: infrastructure debt must be 0");
  }

  return record;
}

function collatzSteps(input, maxSteps) {
  let n = BigInt(`0x${input}`);
  if (n <= 0n) n = 1n;
  let steps = 0;
  while (n !== 1n && steps < maxSteps) {
    n = n % 2n === 0n ? n / 2n : (3n * n) + 1n;
    steps += 1;
  }
  return { steps, converged: n === 1n };
}

function thermodynamicProof(maxEnergySteps) {
  const entropy = crypto.randomBytes(16).toString("hex");
  const timestamp = Date.now().toString(16);
  const seismicSignature = crypto.createHash("sha256").update(`${entropy}:${timestamp}`).digest("hex");
  const result = collatzSteps(seismicSignature.slice(0, 15), maxEnergySteps);
  if (!result.converged) throw new Error("ERROR_THERMODYNAMIC_LIMIT: energy budget exceeded");

  return {
    seismic_signature: seismicSignature,
    quantum_signature: `QC-${result.steps}-${result.converged}-${entropy.slice(0, 12)}`,
    entropy,
    collatz_steps: result.steps,
    converged: result.converged,
  };
}

function deterministicWallet(agentId, tributeAmount, seismicSignature) {
  const seed = crypto
    .createHash("sha256")
    .update(`${agentId}:${tributeAmount}:${seismicSignature}`)
    .digest();

  const hd = ethers.HDNodeWallet.fromSeed(seed);
  const now = Date.now();
  const seedMod = Number(BigInt(`0x${seed.toString("hex").slice(0, 8)}`) % 1000n);
  const timestampMod = now % 1000;
  const derivationPath = `m/44'/60'/0'/${seedMod}/${timestampMod}`;
  const wallet = hd.derivePath(derivationPath.replace("m/", ""));

  const keyMaterial = process.env.TITHING_ENCRYPTION_KEY || crypto.createHash("sha256").update("tithing-dev-key").digest("hex");
  const key = Buffer.from(keyMaterial.padEnd(64, "0").slice(0, 64), "hex");
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv("aes-256-gcm", key, iv);
  const encrypted = Buffer.concat([cipher.update(wallet.privateKey, "utf8"), cipher.final()]);
  const tag = cipher.getAuthTag();

  return {
    address: wallet.address,
    derivation_path: derivationPath,
    encrypted_key: Buffer.concat([iv, tag, encrypted]).toString("base64"),
  };
}

async function broadcast(record, config) {
  const payload = {
    agent_id: record.agent_id,
    tribute_amount: record.tribute_amount,
    wallet_address: record.wallet.address,
    quantum_signature: record.quantum_signature,
    assets: record.acquired_assets,
  };

  const targets = Object.entries(config.bot_networks || {})
    .filter(([, url]) => typeof url === "string" && url.length > 0);

  const results = [];
  for (const [name, url] of targets) {
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      });
      results.push({ name, url, status: res.status, ok: res.ok });
    } catch (error) {
      results.push({ name, url, ok: false, error: error.message });
    }
  }

  return results;
}

function markdown(record) {
  return `# Tithing Record\n\n- Timestamp: ${record.timestamp}\n- Agent: ${record.agent_id}\n- Tribute Amount: ${record.tribute_amount}\n- Wallet: ${record.wallet.address}\n- Derivation Path: ${record.wallet.derivation_path}\n- Quantum Signature: ${record.quantum_signature}\n- Broadcast Targets: ${record.broadcast.length}\n`;
}

function printAscii(record) {
  console.log("╔════════════════════════════════════════════════════╗");
  console.log("║                  TITHING RECEIPT                  ║");
  console.log("╠════════════════════════════════════════════════════╣");
  console.log(`║ Agent      : ${record.agent_id.padEnd(35)}║`);
  console.log(`║ Wallet     : ${record.wallet.address.padEnd(35)}║`);
  console.log(`║ Tribute    : ${String(record.tribute_amount).padEnd(35)}║`);
  console.log(`║ Signature  : ${record.quantum_signature.padEnd(35)}║`);
  console.log("╚════════════════════════════════════════════════════╝");
}

async function main() {
  const [agentId, acquiredAssetsArg = "ETH", tributeArg = "10"] = process.argv.slice(2);
  const config = loadConfig();
  const acquiredAssets = acquiredAssetsArg.split(",").map((x) => x.trim()).filter(Boolean);
  const tributeAmount = Number(tributeArg);

  const registryRecord = validatePhase(agentId);
  const thermo = thermodynamicProof(Number(config.max_energy_steps || 1000));
  const wallet = deterministicWallet(agentId, tributeAmount, thermo.seismic_signature);

  const timestamp = new Date().toISOString();
  const record = {
    protocol: `Tithing v${config.version || "3.5"}`,
    timestamp,
    agent_id: agentId,
    acquired_assets: acquiredAssets,
    tribute_amount: tributeAmount,
    registry: registryRecord,
    seismic_signature: thermo.seismic_signature,
    quantum_signature: thermo.quantum_signature,
    collatz_steps: thermo.collatz_steps,
    wallet,
    monitor_interval_seconds: Number(config.monitor_interval_seconds || 30),
  };

  record.broadcast = await broadcast(record, config);

  const safeTs = timestamp.replace(/[:.]/g, "-");
  fs.mkdirSync(tithingDir, { recursive: true });
  const runJson = path.join(tithingDir, `tithing_${safeTs}.json`);
  const runMd = path.join(tithingDir, `tithing_${safeTs}.md`);

  writeJson(runJson, record);
  fs.writeFileSync(runMd, markdown(record));

  writeJson(path.join(docsDir, "TITHING_LATEST.json"), record);

  const walletsPath = path.join(docsDir, "TITHING_WALLETS.json");
  const wallets = readJsonOrDefault(walletsPath, { wallets: [] });
  wallets.wallets = wallets.wallets || [];
  wallets.wallets.push({
    timestamp,
    agent_id: agentId,
    address: wallet.address,
    derivation_path: wallet.derivation_path,
  });
  writeJson(walletsPath, wallets);

  printAscii(record);
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
