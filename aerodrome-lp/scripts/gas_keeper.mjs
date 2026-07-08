#!/usr/bin/env node
/**
 * gas_keeper.mjs — Keep LP_OWNER gas above activation thresholds using:
 *   1) HD treasury dust consolidation (BACKFILL_MASTER_MNEMONIC indexes)
 *   2) Positive-ROI / LP harvest: removeLiquidity → unwrap WETH → ETH (capped)
 *   3) Idle WETH unwrap
 *
 * Thresholds (env-overridable):
 *   GAS_MIN_ETH      default 0.003   — hard activation floor (resume live txs)
 *   GAS_TARGET_ETH   default 0.01    — preferred operating buffer
 *   GAS_MAX_ETH      default 0.05    — stop topping once above this
 *   MAX_REMOVE_PCT   default 5       — max % of LP removed per cycle
 *   MIN_LP_SHARE_BPS default 5000    — never drop LP ownership below 50% of pool
 *
 * Modes:
 *   --once     single cycle (default for cron)
 *   --loop     continuous (interval GAS_KEEPER_INTERVAL_MS, default 15m)
 *   --dry-run  no broadcasts
 *   --live     broadcast (requires .ARMED + PRIVATE_KEY / mnemonic)
 */
import { ethers } from 'ethers';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..');
const LOG = path.join(ROOT, 'logs', 'gas_keeper.log');
const ARMED = path.join(ROOT, '.ARMED');
const STATE = path.join(ROOT, 'config', 'gas_keeper_state.json');
const DASH = '/dev/shm/lp_dashboard.json';

const RPC = process.env.RPC_URL || 'https://base-rpc.publicnode.com';
const CHAIN_ID = 8453;
const LP_OWNER = '0x60C4499870f115664d7FfD8411b023DBEf3377d9';
const WETH = '0x4200000000000000000000000000000000000006';
const WQFLOP = '0x69262A2D7c92c074729823B654fE7E4Cdb749747';
const POOL = '0x4aBC6D796cd036b6f1E433A97F9784a00f90C53e';
const ROUTER = '0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43';

const GAS_MIN = ethers.parseEther(process.env.GAS_MIN_ETH || '0.003');
const GAS_TARGET = ethers.parseEther(process.env.GAS_TARGET_ETH || '0.01');
const GAS_MAX = ethers.parseEther(process.env.GAS_MAX_ETH || '0.05');
const MAX_RM_PCT = parseFloat(process.env.MAX_REMOVE_PCT || '5');
const MIN_LP_SHARE_BPS = BigInt(process.env.MIN_LP_SHARE_BPS || '5000');
const HD_COUNT = parseInt(process.env.GAS_HD_COUNT || '25', 10);
const HD_RESERVE = ethers.parseEther(process.env.HD_GAS_RESERVE_ETH || '0.00002');
const INTERVAL = parseInt(process.env.GAS_KEEPER_INTERVAL_MS || '900000', 10);

const LIVE = process.argv.includes('--live');
const DRY = process.argv.includes('--dry-run') || !LIVE;
const LOOP = process.argv.includes('--loop');

const ERC20 = [
  'function balanceOf(address) view returns (uint256)',
  'function approve(address,uint256) returns (bool)',
  'function allowance(address,address) view returns (uint256)',
];
const WETH9 = [...ERC20, 'function withdraw(uint256)'];
const POOL_A = [
  'function getReserves() view returns (uint256,uint256,uint256)',
  'function balanceOf(address) view returns (uint256)',
  'function totalSupply() view returns (uint256)',
  'function approve(address,uint256) returns (bool)',
  'function allowance(address,address) view returns (uint256)',
  'function token0() view returns (address)',
];
const ROUTER_A = [
  'function removeLiquidity(address,address,bool,uint256,uint256,uint256,address,uint256) returns (uint256,uint256)',
];

function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}`;
  console.log(line);
  try { fs.appendFileSync(LOG, line + '\n'); } catch {}
}
const fmt = (v) => ethers.formatEther(v);
const delay = (ms) => new Promise((r) => setTimeout(r, ms));

function saveState(s) {
  try {
    fs.mkdirSync(path.dirname(STATE), { recursive: true });
    fs.writeFileSync(STATE, JSON.stringify({ ...s, updated_at: new Date().toISOString() }, null, 2));
  } catch {}
}

function patchDashboard(patch) {
  try {
    let d = {};
    try { d = JSON.parse(fs.readFileSync(DASH, 'utf8')); } catch {}
    d.timestamp = new Date().toISOString();
    d.gas_keeper = patch;
    fs.writeFileSync(DASH, JSON.stringify(d, null, 2));
  } catch {}
}

async function consolidateFromHd(provider, ownerAddr, needWei) {
  const mnemonic = process.env.BACKFILL_MASTER_MNEMONIC;
  if (!mnemonic) {
    log('HD consolidate skip: BACKFILL_MASTER_MNEMONIC unset');
    return { sent: 0n, txs: [] };
  }
  let remaining = needWei;
  let sent = 0n;
  const txs = [];
  for (let i = 0; i < HD_COUNT && remaining > 0n; i++) {
    const w = ethers.HDNodeWallet.fromMnemonic(
      ethers.Mnemonic.fromPhrase(mnemonic),
      `m/44'/60'/0'/0/${i}`,
    ).connect(provider);
    if (w.address.toLowerCase() === ownerAddr.toLowerCase()) continue;
    const bal = await provider.getBalance(w.address);
    if (bal <= HD_RESERVE) continue;
    let xfer = bal - HD_RESERVE;
    // leave headroom for gas of this tx (~0.00002 extra if tight)
    const gasPad = ethers.parseEther('0.000015');
    if (xfer <= gasPad) continue;
    xfer = xfer - gasPad;
    if (xfer > remaining) xfer = remaining;
    if (xfer <= 0n) continue;
    log(`HD${i} ${w.address.slice(0, 10)}… can send ${fmt(xfer)} ETH (bal ${fmt(bal)})`);
    if (DRY) {
      sent += xfer;
      remaining -= xfer;
      txs.push({ from: w.address, amount: fmt(xfer), dry: true });
      continue;
    }
    try {
      const tx = await w.sendTransaction({ to: ownerAddr, value: xfer });
      await tx.wait();
      log(`HD${i} top-up tx ${tx.hash} amount ${fmt(xfer)}`);
      sent += xfer;
      remaining -= xfer;
      txs.push({ from: w.address, amount: fmt(xfer), hash: tx.hash });
    } catch (e) {
      log(`HD${i} send failed: ${e.message.slice(0, 160)}`);
    }
    await delay(1500);
  }
  return { sent, txs };
}

async function unwrapWeth(wallet, amount) {
  if (amount <= 0n) return null;
  const weth = new ethers.Contract(WETH, WETH9, wallet);
  log(`unwrap WETH ${fmt(amount)}`);
  if (DRY) return { dry: true, amount: fmt(amount) };
  const tx = await weth.withdraw(amount);
  await tx.wait();
  log(`unwrap tx ${tx.hash}`);
  return { hash: tx.hash, amount: fmt(amount) };
}

async function harvestLpForGas(wallet, provider, needWei) {
  const pool = new ethers.Contract(POOL, POOL_A, wallet);
  const router = new ethers.Contract(ROUTER, ROUTER_A, wallet);
  const wethC = new ethers.Contract(WETH, WETH9, wallet);

  const [lpBal, total, res, t0] = await Promise.all([
    pool.balanceOf(LP_OWNER),
    pool.totalSupply(),
    pool.getReserves(),
    pool.token0(),
  ]);
  if (lpBal === 0n || total === 0n) {
    log('no LP to harvest');
    return { harvested: 0n };
  }
  const wethIs0 = t0.toLowerCase() === WETH.toLowerCase();
  const wethRes = wethIs0 ? res[0] : res[1];
  const shareBps = (lpBal * 10000n) / total;
  if (shareBps <= MIN_LP_SHARE_BPS) {
    log(`LP share ${shareBps} bps at/under floor ${MIN_LP_SHARE_BPS}; skip harvest`);
    return { harvested: 0n, share_bps: shareBps.toString() };
  }

  // Cap remove so share stays above MIN_LP_SHARE_BPS
  const maxByShare = lpBal - (MIN_LP_SHARE_BPS * total) / 10000n;
  const maxByPct = (lpBal * BigInt(Math.floor(MAX_RM_PCT * 100))) / 10000n;
  let rm = maxByShare < maxByPct ? maxByShare : maxByPct;
  if (rm <= 0n) return { harvested: 0n };

  // Scale remove to needed WETH (+10% buffer)
  const lpWethValue = (lpBal * wethRes) / total;
  if (lpWethValue === 0n) return { harvested: 0n };
  const needWithBuf = (needWei * 110n) / 100n;
  const rmForNeed = (lpBal * needWithBuf) / lpWethValue + 1n;
  if (rmForNeed < rm) rm = rmForNeed;

  const expectWeth = (rm * wethRes) / total;
  const minWeth = (expectWeth * 90n) / 100n;
  log(`LP harvest plan: remove ${fmt(rm)} LP (~${fmt(expectWeth)} WETH), share_bps=${shareBps}`);

  if (DRY) {
    return { harvested: expectWeth, dry: true, lp_removed: fmt(rm) };
  }

  // approve router
  const allowance = await pool.allowance(LP_OWNER, ROUTER);
  if (allowance < rm) {
    const atx = await pool.approve(ROUTER, ethers.MaxUint256);
    await atx.wait();
  }
  const deadline = Math.floor(Date.now() / 1000) + 600;
  const rtx = await router.removeLiquidity(
    WQFLOP, WETH, false, rm, 0n, minWeth, LP_OWNER, deadline,
  );
  const receipt = await rtx.wait();
  log(`removeLiquidity ${rtx.hash}`);
  await delay(1000);
  const wethBal = await wethC.balanceOf(LP_OWNER);
  const unwrapAmt = wethBal > needWithBuf ? needWithBuf : wethBal;
  const u = await unwrapWeth(wallet, unwrapAmt);
  return {
    harvested: unwrapAmt,
    tx: rtx.hash,
    unwrap: u,
    lp_removed: fmt(rm),
    block: receipt.blockNumber,
  };
}

async function cycle() {
  if (LIVE && !fs.existsSync(ARMED)) {
    log('REFUSE live: .ARMED missing');
    return { ok: false, reason: 'not_armed' };
  }
  const pk = process.env.PRIVATE_KEY;
  const provider = new ethers.JsonRpcProvider(RPC, CHAIN_ID);
  if (!pk && LIVE) {
    log('REFUSE live: PRIVATE_KEY missing');
    return { ok: false, reason: 'no_key' };
  }
  const wallet = pk
    ? new ethers.Wallet(pk, provider)
    : null;
  if (wallet && wallet.address.toLowerCase() !== LP_OWNER.toLowerCase()) {
    log(`WARNING signer ${wallet.address} != LP_OWNER`);
  }

  let eth = await provider.getBalance(LP_OWNER);
  const wethC = new ethers.Contract(WETH, WETH9, provider);
  let wethBal = await wethC.balanceOf(LP_OWNER);
  log(`start ETH=${fmt(eth)} WETH=${fmt(wethBal)} min=${fmt(GAS_MIN)} target=${fmt(GAS_TARGET)} mode=${DRY ? 'dry-run' : 'live'}`);

  if (eth >= GAS_TARGET) {
    log('gas at/above target — idle');
    const report = {
      status: 'ok',
      eth: fmt(eth),
      target: fmt(GAS_TARGET),
      min: fmt(GAS_MIN),
      action: 'idle',
    };
    patchDashboard(report);
    saveState(report);
    return report;
  }

  const needToTarget = GAS_TARGET - eth;
  const needToMin = eth < GAS_MIN ? GAS_MIN - eth : 0n;
  const need = needToTarget > needToMin ? needToTarget : needToMin;
  const actions = [];

  // 1) unwrap idle WETH first
  if (wethBal > 0n && eth < GAS_TARGET) {
    const take = wethBal > need ? need : wethBal;
    if (wallet || DRY) {
      const u = await unwrapWeth(wallet || { /* dry */ }, take);
      actions.push({ type: 'unwrap_weth', ...u });
      if (!DRY) {
        eth = await provider.getBalance(LP_OWNER);
        wethBal = await wethC.balanceOf(LP_OWNER);
      } else {
        eth += take;
      }
    }
  }

  // 2) HD treasury consolidation
  if (eth < GAS_TARGET) {
    const still = GAS_TARGET - eth;
    const c = await consolidateFromHd(provider, LP_OWNER, still);
    actions.push({ type: 'hd_consolidate', sent: fmt(c.sent), txs: c.txs });
    if (!DRY && c.sent > 0n) eth = await provider.getBalance(LP_OWNER);
    else if (DRY) eth += c.sent;
  }

  // 3) LP harvest ONLY when below activation floor (never cannibalize LP just to hit 0.01 target)
  // Positive ROI path: only peel LP when gas would otherwise stall live ops.
  if (eth < GAS_MIN && (wallet || DRY)) {
    const still = GAS_MIN - eth;
    // small buffer above min so we don't re-harvest every cycle
    const want = still + (GAS_MIN / 5n);
    const h = await harvestLpForGas(wallet || {}, provider, want);
    actions.push({ type: 'lp_harvest', ...h });
    if (!DRY) eth = await provider.getBalance(LP_OWNER);
    else if (h.harvested) eth += h.harvested;
  } else if (eth < GAS_TARGET) {
    log(`ETH ${fmt(eth)} above min ${fmt(GAS_MIN)} but below target ${fmt(GAS_TARGET)} — waiting for external top-up / fee ROI (no LP peel)`);
    actions.push({ type: 'wait_external_or_roi', eth: fmt(eth), target: fmt(GAS_TARGET) });
  }

  const report = {
    status: eth >= GAS_MIN ? (eth >= GAS_TARGET ? 'ok' : 'partial') : 'below_min',
    eth: fmt(eth),
    min: fmt(GAS_MIN),
    target: fmt(GAS_TARGET),
    shortfall_to_target: eth < GAS_TARGET ? fmt(GAS_TARGET - eth) : '0',
    actions,
    note: eth < GAS_TARGET
      ? 'Onchain treasuries insufficient for full 0.01 target; loop will retry as ROI/LP accrues or external fund lands'
      : 'gas healthy',
  };
  log(`end ETH≈${report.eth} status=${report.status} ${report.note}`);
  patchDashboard(report);
  saveState(report);
  return report;
}

async function main() {
  log(`gas_keeper start live=${LIVE} dry=${DRY} loop=${LOOP}`);
  if (LOOP) {
    for (;;) {
      try { await cycle(); } catch (e) { log(`cycle error: ${e.message}`); }
      log(`sleep ${INTERVAL}ms`);
      await delay(INTERVAL);
    }
  } else {
    await cycle();
  }
}

main().catch((e) => {
  log(`fatal: ${e.message}`);
  process.exit(1);
});
