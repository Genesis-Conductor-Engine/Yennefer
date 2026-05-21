#!/usr/bin/env node
/**
 * B5 — lp_unwind: plan a single Aerodrome removeLiquidity to evacuate an LP
 * position to the Safe. Dry-run by default. Broadcast is double-gated.
 *
 * ROLE SAFETY: the canonical Aerodrome Router on Base is
 *   0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43
 *   (source: https://aerodrome.finance — "Router"; verify on
 *    https://basescan.org/address/0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43 )
 * That address is the ROUTER, NOT a pool. The DECISIONS doc listed it as the
 * "pool" — that is a conflation. This script verifies pool-vs-router roles on
 * chain and FAILS CLOSED (emits a TODO + non-zero exit) rather than guessing the
 * pool. Supply the real LP token via POOL_ADDRESS.
 *
 * Env:
 *   SAFE_ADDRESS (required)         — destination; TO_ADDRESS must equal this
 *   POOL_ADDRESS (required)         — the Aerodrome LP token / pool to unwind
 *   FROM_ADDRESS (default 0x9545…6956) — LP holder
 *   TO_ADDRESS   (default = SAFE_ADDRESS)
 *   AERODROME_ROUTER (default canonical above; verified at runtime)
 *   SLIPPAGE_BPS (default 50 = 0.5%)
 *   BASE_MAINNET_RPC|BASE_RPC_URL
 * Flags: --broadcast  (also needs env I_UNDERSTAND_IRREVERSIBLE=yes)
 */
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { ethers } = require('ethers');

const RPC = process.env.BASE_MAINNET_RPC || process.env.BASE_RPC_URL || 'https://mainnet.base.org';
const ROUTER_DEFAULT = '0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43';
const DEFAULT_FROM = '0x9545e2439c5c75d3aA723AcaC1AA6B0fa1DB6956';
const ts = () => new Date().toISOString();
const out = (o) => process.stdout.write(JSON.stringify({ ...o, ts: ts() }) + '\n');
function fail(reason, extra) {
  out({ step: 'lp_unwind', ok: false, mode: 'dry-run', reason, ...(extra || {}) });
  process.exit(1);
}

const POOL_ABI = [
  'function token0() view returns (address)',
  'function token1() view returns (address)',
  'function stable() view returns (bool)',
  'function totalSupply() view returns (uint256)',
  'function getReserves() view returns (uint256,uint256,uint256)',
  'function balanceOf(address) view returns (uint256)',
  'function allowance(address,address) view returns (uint256)',
  'function decimals() view returns (uint8)',
];
const ROUTER_ABI = [
  'function defaultFactory() view returns (address)',
  'function removeLiquidity(address tokenA,address tokenB,bool stable,uint256 liquidity,uint256 amountAMin,uint256 amountBMin,address to,uint256 deadline) returns (uint256 amountA,uint256 amountB)',
];
const ERC20_APPROVE_ABI = ['function approve(address spender,uint256 amount) returns (bool)'];

function ensureSafeVerified(safe) {
  const cache = path.join(process.cwd(), '.yennefer-cache', 'safe.json');
  let fresh = false;
  if (fs.existsSync(cache)) {
    try {
      const j = JSON.parse(fs.readFileSync(cache, 'utf8'));
      const ageMs = Date.now() - new Date(j.verified_at).getTime();
      fresh = j.address && j.address.toLowerCase() === safe.toLowerCase() && ageMs < 3600_000;
    } catch { /* stale */ }
  }
  if (!fresh) {
    execFileSync('node', ['scripts/verify_safe.cjs'], {
      env: { ...process.env, SAFE_ADDRESS: safe }, stdio: ['ignore', 'inherit', 'inherit'],
    }); // throws (non-zero) if verification fails -> aborts unwind
  }
}

async function main() {
  const broadcast = process.argv.includes('--broadcast');
  const safe = process.env.SAFE_ADDRESS;
  if (!safe || !/^0x[0-9a-fA-F]{40}$/.test(safe)) fail('SAFE_ADDRESS unset/malformed');
  const to = process.env.TO_ADDRESS || safe;
  if (to.toLowerCase() !== safe.toLowerCase()) fail('TO_ADDRESS must equal SAFE_ADDRESS');
  const from = process.env.FROM_ADDRESS || DEFAULT_FROM;
  if (!/^0x[0-9a-fA-F]{40}$/.test(from)) fail('FROM_ADDRESS malformed');

  const poolAddr = process.env.POOL_ADDRESS;
  if (!poolAddr || !/^0x[0-9a-fA-F]{40}$/.test(poolAddr)) {
    return fail('POOL_ADDRESS unset — the LP token/pool address is required and was not verified',
      { todo: 'find the real wQFLOP/ETH Aerodrome LP token (NOT the router 0xcF77…874E43) and set POOL_ADDRESS. Verify at https://aerodrome.finance/liquidity or https://basescan.org' });
  }
  const slippageBps = BigInt(process.env.SLIPPAGE_BPS || '50');

  // Gate: Safe must verify before we plan a transfer to it.
  ensureSafeVerified(ethers.getAddress(safe));

  const provider = new ethers.JsonRpcProvider(RPC);
  const net = await provider.getNetwork();
  if (net.chainId !== 8453n) fail(`RPC chainId ${net.chainId} != 8453`);

  // Verify ROUTER role (must expose defaultFactory()).
  const routerAddr = process.env.AERODROME_ROUTER || ROUTER_DEFAULT;
  const router = new ethers.Contract(routerAddr, ROUTER_ABI, provider);
  try { await router.defaultFactory(); }
  catch { return fail(`AERODROME_ROUTER ${routerAddr} does not expose defaultFactory() — not a router`,
    { todo: 'set AERODROME_ROUTER to the canonical Aerodrome Router on Base; verify on basescan' }); }

  // Verify POOL role (must expose token0/token1/getReserves). The router will fail here.
  const pool = new ethers.Contract(poolAddr, POOL_ABI, provider);
  let token0, token1, stable, totalSupply, reserves, lpAmount;
  try {
    [token0, token1, stable, totalSupply, reserves, lpAmount] = await Promise.all([
      pool.token0(), pool.token1(), pool.stable(), pool.totalSupply(),
      pool.getReserves(), pool.balanceOf(from),
    ]);
  } catch (e) {
    return fail(`POOL_ADDRESS ${poolAddr} is not an Aerodrome pool (token0/getReserves reverted): ${e.shortMessage || e.message}`,
      { todo: 'POOL_ADDRESS may be the router or a non-pool. Supply the real LP token address.' });
  }

  if (lpAmount === 0n) return fail(`FROM ${from} holds 0 LP tokens in pool ${poolAddr}`);

  // Proportional share from reserves, minus slippage.
  const reserve0 = reserves[0], reserve1 = reserves[1];
  const amount0 = (reserve0 * lpAmount) / totalSupply;
  const amount1 = (reserve1 * lpAmount) / totalSupply;
  const amount0Min = (amount0 * (10000n - slippageBps)) / 10000n;
  const amount1Min = (amount1 * (10000n - slippageBps)) / 10000n;
  const deadline = Math.floor(Date.now() / 1000) + 1200;

  // Approval check -> plan approve() as tx[0] if needed.
  const allowance = await pool.allowance(from, routerAddr);
  const bundle = [];
  if (allowance < lpAmount) {
    const erc20 = new ethers.Contract(poolAddr, ERC20_APPROVE_ABI, provider);
    bundle.push({
      idx: bundle.length, kind: 'approve', to: poolAddr,
      data: erc20.interface.encodeFunctionData('approve', [routerAddr, lpAmount]),
    });
  }
  bundle.push({
    idx: bundle.length, kind: 'removeLiquidity', to: routerAddr,
    data: router.interface.encodeFunctionData('removeLiquidity',
      [token0, token1, stable, lpAmount, amount0Min, amount1Min, ethers.getAddress(to), deadline]),
  });

  // Gas sufficiency: FROM must hold enough ETH for the bundle.
  const feeData = await provider.getFeeData();
  const gasPrice = feeData.maxFeePerGas || feeData.gasPrice || 0n;
  let totalGas = 0n;
  for (const b of bundle) {
    let g = b.kind === 'approve' ? 60000n : 250000n;
    try { g = await provider.estimateGas({ from, to: b.to, data: b.data }); } catch { /* keep heuristic */ }
    b.gas = g.toString();
    totalGas += g;
  }
  const ethBal = await provider.getBalance(from);
  const gasCost = totalGas * gasPrice;
  const gasOk = ethBal >= gasCost;

  const plan = {
    from, to: ethers.getAddress(to), router: routerAddr, pool: poolAddr,
    token0, token1, stable, lpAmount: lpAmount.toString(),
    expected_token0: amount0.toString(), expected_token1: amount1.toString(),
    amount0Min: amount0Min.toString(), amount1Min: amount1Min.toString(),
    slippage_bps: slippageBps.toString(), deadline,
    bundle, est_gas: totalGas.toString(), est_gas_cost_wei: gasCost.toString(),
    eth_balance_wei: ethBal.toString(), gas_sufficient: gasOk,
  };
  fs.mkdirSync(path.join(process.cwd(), 'out'), { recursive: true });
  fs.writeFileSync(path.join(process.cwd(), 'out', 'lp_unwind_plan.json'), JSON.stringify(plan, null, 2));
  process.stderr.write(JSON.stringify(plan, null, 2) + '\n');

  if (!gasOk) {
    return fail(`insufficient ETH for gas: have ${ethers.formatEther(ethBal)}, need ~${ethers.formatEther(gasCost)}`,
      { lp_amount: lpAmount.toString(), expected_token0: amount0.toString(), expected_token1: amount1.toString() });
  }

  if (!broadcast) {
    out({ step: 'lp_unwind', ok: true, mode: 'dry-run', lp_amount: lpAmount.toString(),
      expected_token0: amount0.toString(), expected_token1: amount1.toString(), tx_hash: null });
    return;
  }

  // ── BROADCAST (gated; owner-run only) ──
  if (process.env.I_UNDERSTAND_IRREVERSIBLE !== 'yes') {
    return fail('--broadcast requires env I_UNDERSTAND_IRREVERSIBLE=yes', { mode_attempted: 'broadcast' });
  }
  const rawKey = process.env.ETH_PRIVATE_KEY || process.env.BASE_PRIVATE_KEY || '';
  if (!/^0x[0-9a-fA-F]{64}$/.test(rawKey)) {
    return fail('no signing key in env (ETH_PRIVATE_KEY) — cannot broadcast', { mode_attempted: 'broadcast' });
  }
  const signer = new ethers.Wallet(rawKey, provider);
  let lastHash = null;
  for (const b of bundle) {
    const tx = await signer.sendTransaction({ to: b.to, data: b.data });
    lastHash = tx.hash;
    await tx.wait();
  }
  out({ step: 'lp_unwind', ok: true, mode: 'broadcast', lp_amount: lpAmount.toString(),
    expected_token0: amount0.toString(), expected_token1: amount1.toString(), tx_hash: lastHash });
}

main().catch((e) => fail(e.message));
