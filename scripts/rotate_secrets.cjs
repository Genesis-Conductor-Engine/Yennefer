#!/usr/bin/env node
/**
 * A1 — rotate_secrets: verify NEW api credentials and write them to a 0600,
 * gitignored env file outside the repo. Does NOT touch the live dashboards
 * (revoking the OLD keys is a manual step Igor performs in Etherscan/Alchemy).
 *
 * Env (required):
 *   NEW_ETHERSCAN_KEY, NEW_ALCHEMY_KEY, NEW_ALCHEMY_RPC_URL
 *
 * Output file: ~/.yennefer/.env.local  (0600)
 * Idempotent: identical inputs => byte-identical file (modulo nothing; ts only in JSONL).
 */
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const ts = () => new Date().toISOString();
const out = (o) => process.stdout.write(JSON.stringify({ ...o, ts: ts() }) + '\n');
function die(reason) { out({ step: 'rotate_secrets', ok: false, reason }); process.exit(1); }

async function main() {
  const etherscanKey = process.env.NEW_ETHERSCAN_KEY;
  const alchemyKey = process.env.NEW_ALCHEMY_KEY;
  const alchemyRpc = process.env.NEW_ALCHEMY_RPC_URL;
  if (!etherscanKey) die('NEW_ETHERSCAN_KEY unset');
  if (!alchemyKey) die('NEW_ALCHEMY_KEY unset');
  if (!alchemyRpc || !/^https:\/\//.test(alchemyRpc)) die('NEW_ALCHEMY_RPC_URL unset or not https');

  // --- Verify Etherscan key ---
  let res;
  try {
    res = await fetch(`https://api.etherscan.io/api?module=stats&action=ethsupply&apikey=${etherscanKey}`);
  } catch (e) { die(`etherscan request failed: ${e.message}`); }
  if (res.status === 401 || res.status === 403) die(`etherscan auth failed: HTTP ${res.status}`);
  const ej = await res.json().catch(() => ({}));
  // Etherscan returns 200 + status "0" + "Invalid API Key" for bad keys.
  if (ej.status === '0' && /invalid api key/i.test(ej.result || '')) die('etherscan: invalid api key');
  const etherscanOk = res.status === 200 && (ej.status === '1' || typeof ej.result === 'string');

  // --- Verify Alchemy Base RPC (eth_chainId == 0x2105) ---
  let rpcRes;
  try {
    rpcRes = await fetch(alchemyRpc, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'eth_chainId', params: [] }),
    });
  } catch (e) { die(`alchemy request failed: ${e.message}`); }
  if (rpcRes.status === 401 || rpcRes.status === 403) die(`alchemy auth failed: HTTP ${rpcRes.status}`);
  const rj = await rpcRes.json().catch(() => ({}));
  if (rj.result !== '0x2105') die(`alchemy chainId mismatch: got ${rj.result}, expected 0x2105 (Base 8453)`);

  if (!etherscanOk) die('etherscan verification inconclusive');

  // --- Write env file (deterministic, sorted, 0600) ---
  const dir = path.join(os.homedir(), '.yennefer');
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, '.env.local');
  const lines = [
    `ALCHEMY_API_KEY=${alchemyKey}`,
    `BASE_MAINNET_RPC=${alchemyRpc}`,
    `ETHERSCAN_API_KEY=${etherscanKey}`,
  ].sort();
  fs.writeFileSync(file, lines.join('\n') + '\n', { mode: 0o600 });
  fs.chmodSync(file, 0o600);

  out({ step: 'rotate_secrets', ok: true, etherscan: 'ok', alchemy: 'ok', file });
}

main().catch((e) => die(e.message));
