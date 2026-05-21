#!/usr/bin/env node
/**
 * B2 — verify_safe: confirm SAFE_ADDRESS is a real, sane Gnosis Safe on Base.
 * Fails CLOSED (non-zero exit) on any mismatch. Read-only.
 *
 * Checks:
 *   - Safe Transaction Service: /api/v1/safes/{address}/ resolves (=> deployed on Base)
 *   - threshold >= 2
 *   - owners.length >= threshold
 *   - nonce >= 0 (exists)
 *   - eth_call cross-check: getOwners()/getThreshold() on Base RPC match the API
 *
 * Env: SAFE_ADDRESS (required), BASE_MAINNET_RPC|BASE_RPC_URL (optional, default public)
 * Side effect: writes .yennefer-cache/safe.json on success.
 */
const fs = require('node:fs');
const path = require('node:path');
const { ethers } = require('ethers');

const RPC = process.env.BASE_MAINNET_RPC || process.env.BASE_RPC_URL || 'https://mainnet.base.org';
const SAFE_TX_API = 'https://safe-transaction-base.safe.global';
const ts = () => new Date().toISOString();
const out = (o) => process.stdout.write(JSON.stringify({ ...o, ts: ts() }) + '\n');
function fail(address, reason) {
  out({ step: 'verify_safe', ok: false, address: address || null, reason });
  process.exit(1);
}

const SAFE_ABI = [
  'function getOwners() view returns (address[])',
  'function getThreshold() view returns (uint256)',
];

async function main() {
  const raw = process.env.SAFE_ADDRESS;
  if (!raw || !/^0x[0-9a-fA-F]{40}$/.test(raw)) fail(raw, 'SAFE_ADDRESS unset or malformed');
  let address;
  try { address = ethers.getAddress(raw); } catch { return fail(raw, 'SAFE_ADDRESS not checksummable'); }

  // 1. Safe Transaction Service (existence + Base deployment)
  let api;
  try {
    const res = await fetch(`${SAFE_TX_API}/api/v1/safes/${address}/`);
    if (res.status === 404) return fail(address, 'not found on Safe TX Service (not deployed on Base)');
    if (!res.ok) return fail(address, `Safe TX Service HTTP ${res.status}`);
    api = await res.json();
  } catch (e) { return fail(address, `Safe TX Service request failed: ${e.message}`); }

  const apiThreshold = Number(api.threshold);
  const apiOwners = Array.isArray(api.owners) ? api.owners : [];
  const apiNonce = Number(api.nonce);
  if (!(apiThreshold >= 2)) return fail(address, `threshold ${apiThreshold} < 2`);
  if (!(apiOwners.length >= apiThreshold)) return fail(address, `owners ${apiOwners.length} < threshold ${apiThreshold}`);
  if (!(apiNonce >= 0)) return fail(address, `nonce ${api.nonce} invalid`);

  // 2. eth_call cross-check on Base RPC
  let chainOwners, chainThreshold;
  try {
    const provider = new ethers.JsonRpcProvider(RPC);
    const net = await provider.getNetwork();
    if (net.chainId !== 8453n) return fail(address, `RPC chainId ${net.chainId} != 8453`);
    const safe = new ethers.Contract(address, SAFE_ABI, provider);
    [chainOwners, chainThreshold] = await Promise.all([safe.getOwners(), safe.getThreshold()]);
  } catch (e) { return fail(address, `on-chain cross-check failed: ${e.shortMessage || e.message}`); }

  if (Number(chainThreshold) !== apiThreshold) {
    return fail(address, `threshold mismatch: api ${apiThreshold} vs chain ${chainThreshold}`);
  }
  if (chainOwners.length !== apiOwners.length) {
    return fail(address, `owner-count mismatch: api ${apiOwners.length} vs chain ${chainOwners.length}`);
  }

  // 3. Cache for downstream single-pass consumers
  const cacheDir = path.join(process.cwd(), '.yennefer-cache');
  fs.mkdirSync(cacheDir, { recursive: true });
  const payload = {
    address, threshold: apiThreshold, owners: apiOwners.length,
    chainId: 8453, verified_at: ts(),
  };
  fs.writeFileSync(path.join(cacheDir, 'safe.json'), JSON.stringify(payload, null, 2));

  out({ step: 'verify_safe', ok: true, address, threshold: apiThreshold, owners: apiOwners.length, chainId: 8453 });
}

main().catch((e) => fail(process.env.SAFE_ADDRESS, e.message));
