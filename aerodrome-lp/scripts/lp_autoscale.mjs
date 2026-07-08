#!/usr/bin/env node
/**
 * lp_autoscale.mjs — Automated LP scaling for wQFLOP/WETH Aerodrome pool.
 * 
 * Strategy:
 * 1. Swap a portion of wQFLOP → WETH via Aerodrome (generate paired WETH)
 * 2. Add the WETH + proportional wQFLOP as LP
 * 3. Log every action and generate a dashboard JSON
 * 4. Propagate status to MCP / claws
 *
 * Usage: node lp_autoscale.mjs [--dry-run] [--swap-pct N]
 * ENV: PRIVATE_KEY, RPC_URL
 */
import { ethers } from 'ethers';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// --- Config ---
const RPC = process.env.RPC_URL || 'https://mainnet.base.org';
const CHAIN_ID = 8453;
const LP_OWNER = '0x60C4499870f115664d7FfD8411b023DBEf3377d9';

const WETH_ADDR   = '0x4200000000000000000000000000000000000006';
const WQFLOP_ADDR = '0x69262A2D7c92c074729823B654fE7E4Cdb749747';
const POOL_ADDR   = '0x4aBC6D796cd036b6f1E433A97F9784a00f90C53e';
const ROUTER_ADDR = '0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43';
const FACTORY     = '0x420DD381b31aEf6683db6B902084cB0FFECe40Da';

const ERC20_ABI = [
  'function balanceOf(address) view returns (uint256)',
  'function approve(address,uint256) returns (bool)',
  'function allowance(address,address) view returns (uint256)',
];

const ROUTER_ABI = [
  'function swapExactTokensForTokens(uint256 amountIn, uint256 amountOutMin, (address from, address to, bool stable, address factory)[] routes, address to, uint256 deadline) returns (uint256[] amounts)',
  'function addLiquidity(address tokenA, address tokenB, bool stable, uint256 amountADesired, uint256 amountBDesired, uint256 amountAMin, uint256 amountBMin, address to, uint256 deadline) returns (uint256 amountA, uint256 amountB, uint256 liquidity)',
  'function getAmountsOut(uint256 amountIn, (address from, address to, bool stable, address factory)[] routes) view returns (uint256[] amounts)',
];

const POOL_ABI = [
  'function getReserves() view returns (uint256, uint256, uint256)',
  'function balanceOf(address) view returns (uint256)',
  'function totalSupply() view returns (uint256)',
];

const DASHBOARD_PATH = '/dev/shm/lp_dashboard.json';
const LOG_PATH = path.join(__dirname, '..', 'logs', 'lp_autoscale.log');

function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}`;
  console.log(line);
  try { fs.appendFileSync(LOG_PATH, line + '\n'); } catch {}
}

async function runCycle() {
  const dryRun = process.argv.includes('--dry-run');
  const swapPct = parseFloat(process.argv.find(a => a.startsWith('--swap-pct'))?.split('=')[1] || '0.5');
  const dashboardOnly = process.argv.includes('--dashboard');

  // Prefer PRIVATE_KEY for live writes. Without it, stay online in read/dry-run mode
  // (signing for live forge path uses foundry keystore SIGNER_ACCOUNT=qflop-lp).
  const pk = process.env.PRIVATE_KEY;
  const forceLive = process.env.LP_FORCE_LIVE === '1' || process.argv.includes('--live');
  let dry = dryRun || !pk || process.env.LP_DRY_RUN === '1';
  if (!pk) {
    log('PRIVATE_KEY not set — running read-only / dry-run cycle (set PRIVATE_KEY or use workflow.sh + SIGNER_ACCOUNT for live)');
    dry = true;
  }

  const provider = new ethers.JsonRpcProvider(RPC, CHAIN_ID);
  const signerOrProvider = pk ? new ethers.Wallet(pk, provider) : provider;

  const weth   = new ethers.Contract(WETH_ADDR, ERC20_ABI, signerOrProvider);
  const wqflop = new ethers.Contract(WQFLOP_ADDR, ERC20_ABI, signerOrProvider);
  const pool   = new ethers.Contract(POOL_ADDR, POOL_ABI, signerOrProvider);
  const router = new ethers.Contract(ROUTER_ADDR, ROUTER_ABI, signerOrProvider);

  // Fetch state sequentially to avoid RPC rate limiting
  const delay = (ms) => new Promise(r => setTimeout(r, ms));
  let wethBal, wqflopBal, lpBal, reserves, totalSupply, ethBal;
  const maxRetries = 3;
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      wethBal = await weth.balanceOf(LP_OWNER); await delay(1500);
      wqflopBal = await wqflop.balanceOf(LP_OWNER); await delay(1500);
      lpBal = await pool.balanceOf(LP_OWNER); await delay(1500);
      reserves = await pool.getReserves(); await delay(1500);
      totalSupply = await pool.totalSupply(); await delay(1500);
      ethBal = await provider.getBalance(LP_OWNER);
      break;
    } catch (e) {
      log(`Fetch attempt ${attempt + 1}/${maxRetries} failed: ${e.message}`);
      if (attempt === maxRetries - 1) throw e;
      await delay(5000 * (attempt + 1));
    }
  }

  const [r0, r1] = [reserves[0], reserves[1]]; // WETH, wQFLOP

  const dashboard = {
    timestamp: new Date().toISOString(),
    lp_owner: LP_OWNER,
    pool: POOL_ADDR,
    balances: {
      eth: ethers.formatEther(ethBal),
      weth: ethers.formatEther(wethBal),
      wqflop: ethers.formatEther(wqflopBal),
      lp_tokens: ethers.formatEther(lpBal),
    },
    pool_state: {
      reserve_weth: ethers.formatEther(r0),
      reserve_wqflop: ethers.formatEther(r1),
      total_lp_supply: ethers.formatEther(totalSupply),
      lp_share_pct: (Number(lpBal) / Number(totalSupply) * 100).toFixed(4),
      ratio_wqflop_per_weth: (Number(r1) / Number(r0)).toFixed(2),
    },
    last_action: 'dashboard_refresh',
    actions: [],
  };

  log(`LP Position: ${ethers.formatEther(lpBal)} LP tokens (${dashboard.pool_state.lp_share_pct}% of pool)`);
  log(`Balances: ${ethers.formatEther(ethBal)} ETH | ${ethers.formatEther(wethBal)} WETH | ${ethers.formatEther(wqflopBal)} wQFLOP`);
  log(`Pool: ${ethers.formatEther(r0)} WETH + ${ethers.formatEther(r1)} wQFLOP`);

  if (dashboardOnly) {
    fs.writeFileSync(DASHBOARD_PATH, JSON.stringify(dashboard, null, 2));
    log(`Dashboard written to ${DASHBOARD_PATH}`);
    return dashboard;
  }

  // --- Swap wQFLOP → WETH to generate paired liquidity ---
  // Cap at 5% of pool's wQFLOP reserve to avoid draining all WETH
  const maxSwapByPool = r1 / 20n;   // 5% of pool wQFLOP reserve
  const maxSwapByWallet = wqflopBal / 200n;  // 0.5% of wallet per cycle
  const swapAmount = maxSwapByPool < maxSwapByWallet ? maxSwapByPool : maxSwapByWallet;

  if (swapAmount === 0n) {
    log('No wQFLOP available to swap');
    fs.writeFileSync(DASHBOARD_PATH, JSON.stringify(dashboard, null, 2));
    return dashboard;
  }

  // Get quote
  const routes = [{ from: WQFLOP_ADDR, to: WETH_ADDR, stable: false, factory: FACTORY }];
  let amounts; try { amounts = await router.getAmountsOut(swapAmount, routes); } catch(e){ log("getAmountsOut skipped (degen/rate): "+e.message); amounts=[0n,0n]; }
  const expectedWeth = amounts[1];

  log(`Swap quote: ${ethers.formatEther(swapAmount)} wQFLOP → ${ethers.formatEther(expectedWeth)} WETH`);

  if (expectedWeth === 0n) {
    log('Swap would yield 0 WETH — pool too thin');
    fs.writeFileSync(DASHBOARD_PATH, JSON.stringify(dashboard, null, 2));
    return dashboard;
  }

  // Gas floor: ~0.000003 ETH needed historically; block live if underfunded
  const MIN_GAS_WEI = 3_000_000_000_000n; // 0.000003 ETH
  if (!dry && ethBal < MIN_GAS_WEI) {
    log(`ETH gas too low (${ethers.formatEther(ethBal)}); forcing dry-run until LP_OWNER funded`);
    dry = true;
  }
  if (!forceLive && dry) {
    log('[DRY RUN] Would swap + add LP');
    dashboard.last_action = 'dry_run';
    dashboard.actions.push({
      type: 'swap_quote',
      wqflop_in: ethers.formatEther(swapAmount),
      weth_out: ethers.formatEther(expectedWeth),
      eth_balance: ethers.formatEther(ethBal),
      note: pk ? 'gas_or_flag' : 'no_private_key',
    });
    // Accrual progress toward 1 ETH goal (LP share of WETH reserve + wallet ETH/WETH)
    const lpShare = totalSupply > 0n ? (lpBal * 10_000n) / totalSupply : 0n;
    const lpWethValue = (r0 * lpShare) / 10_000n;
    const totalEthEq = ethBal + wethBal + lpWethValue;
    dashboard.goal = {
      target_eth: '1.0',
      accrued_eth_eq: ethers.formatEther(totalEthEq),
      progress_pct: (Number(ethers.formatEther(totalEthEq)) * 100).toFixed(4),
      components: {
        wallet_eth: ethers.formatEther(ethBal),
        wallet_weth: ethers.formatEther(wethBal),
        lp_weth_share: ethers.formatEther(lpWethValue),
      },
    };
    fs.writeFileSync(DASHBOARD_PATH, JSON.stringify(dashboard, null, 2));
    return dashboard;
  }
  if (!pk) {
    log('Cannot execute live without PRIVATE_KEY');
    fs.writeFileSync(DASHBOARD_PATH, JSON.stringify(dashboard, null, 2));
    return dashboard;
  }

  // Approve router for wQFLOP if needed (with retry for RPC rate limiting)
  let allowance;
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      await delay(2000);
      allowance = await wqflop.allowance(LP_OWNER, ROUTER_ADDR);
      break;
    } catch (e) {
      log(`Allowance check attempt ${attempt + 1} failed: ${e.message}`);
      if (attempt === maxRetries - 1) { log('Skipping this cycle due to RPC issues'); return dashboard; }
      await delay(5000 * (attempt + 1));
    }
  }
  if (allowance < swapAmount) {
    log('Approving wQFLOP for Router...');
    const approveTx = await wqflop.approve(ROUTER_ADDR, ethers.MaxUint256);
    await approveTx.wait();
    log('Approved');
  }

  // Execute swap
  const deadline = Math.floor(Date.now() / 1000) + 600;
  log('Executing swap...');
  const swapTx = await router.swapExactTokensForTokens(
    swapAmount, 0n, routes, LP_OWNER, deadline
  );
  const swapReceipt = await swapTx.wait();
  log(`Swap confirmed: ${swapReceipt.hash} block ${swapReceipt.blockNumber}`);

  dashboard.actions.push({
    type: 'swap',
    tx: swapReceipt.hash,
    block: swapReceipt.blockNumber,
    wqflop_in: ethers.formatEther(swapAmount),
    weth_out: ethers.formatEther(expectedWeth),
  });

  // Now add LP with the new WETH + proportional wQFLOP
  const newWethBal = await weth.balanceOf(LP_OWNER);
  const newReserves = await pool.getReserves();
  const wethForLP = newWethBal * 90n / 100n; // Use 90% of WETH
  const wqflopForLP = wethForLP * newReserves[1] / newReserves[0];

  const newWqflopBal = await wqflop.balanceOf(LP_OWNER);
  const actualWqflop = wqflopForLP > newWqflopBal ? newWqflopBal : wqflopForLP;
  const actualWeth = actualWqflop * newReserves[0] / newReserves[1];

  if (actualWeth === 0n || actualWqflop === 0n) {
    log('Insufficient for LP add after swap');
    fs.writeFileSync(DASHBOARD_PATH, JSON.stringify(dashboard, null, 2));
    return dashboard;
  }

  // Approve WETH
  const wethAllowance = await weth.allowance(LP_OWNER, ROUTER_ADDR);
  if (wethAllowance < actualWeth) {
    const approveTx2 = await weth.approve(ROUTER_ADDR, ethers.MaxUint256);
    await approveTx2.wait();
  }

  log(`Adding LP: ${ethers.formatEther(actualWeth)} WETH + ${ethers.formatEther(actualWqflop)} wQFLOP`);
  const minWeth = actualWeth * 95n / 100n;
  const minWqflop = actualWqflop * 95n / 100n;

  const addTx = await router.addLiquidity(
    WQFLOP_ADDR, WETH_ADDR, false,
    actualWqflop, actualWeth,
    minWqflop, minWeth,
    LP_OWNER, deadline
  );
  const addReceipt = await addTx.wait();
  log(`LP added: ${addReceipt.hash} block ${addReceipt.blockNumber}`);

  // Final state
  const finalLp = await pool.balanceOf(LP_OWNER);
  const finalSupply = await pool.totalSupply();
  dashboard.actions.push({
    type: 'add_liquidity',
    tx: addReceipt.hash,
    block: addReceipt.blockNumber,
    weth_added: ethers.formatEther(actualWeth),
    wqflop_added: ethers.formatEther(actualWqflop),
    lp_tokens_after: ethers.formatEther(finalLp),
    share_pct: (Number(finalLp) / Number(finalSupply) * 100).toFixed(4),
  });

  dashboard.last_action = 'swap_and_add_lp';
  dashboard.balances.lp_tokens = ethers.formatEther(finalLp);
  dashboard.pool_state.lp_share_pct = (Number(finalLp) / Number(finalSupply) * 100).toFixed(4);

  fs.writeFileSync(DASHBOARD_PATH, JSON.stringify(dashboard, null, 2));
  log(`Dashboard updated. LP: ${ethers.formatEther(finalLp)} tokens (${dashboard.pool_state.lp_share_pct}%)`);

  return dashboard;
}

async function main() {
  const intervalMs = parseInt(process.env.LP_CYCLE_INTERVAL_MS || '1800000', 10); // 30 min default
  log(`Starting LP autoscale (interval: ${intervalMs / 60000} min)`);

  while (true) {
    try {
      await runCycle();
    } catch (e) {
      log(`Cycle error (non-fatal): ${e.message}`);
    }
    log(`Sleeping ${intervalMs / 60000} min until next cycle...`);
    await new Promise(r => setTimeout(r, intervalMs));
  }
}

main().catch(e => { log(`Fatal: ${e.message}`); process.exit(1); });
