#!/usr/bin/env node
/**
 * secure_sweep — evacuate assets from a (possibly compromised) hot wallet to a
 * secure destination (your Ledger / Safe), as part of key rotation.
 *
 * SAFETY MODEL:
 *   - DRY-RUN by default: builds + simulates + prints. Sends NOTHING.
 *   - Broadcasting is DOUBLE-GATED and must be run BY YOU:
 *       --broadcast  AND  env I_UNDERSTAND_IRREVERSIBLE=yes
 *   - The hot key is read from YOUR env (ETH_PRIVATE_KEY) at run time. This
 *     script (and Claude) never store, log, or transmit it anywhere.
 *   - Transfers are irreversible. Review the dry-run plan before broadcasting.
 *
 * Usage (dry-run, no key needed):
 *   node scripts/secure_sweep.cjs --to 0xLEDGER --from 0xHOTWALLET
 *
 * Usage (broadcast — YOU run this, with your key in env):
 *   ETH_PRIVATE_KEY=0x... I_UNDERSTAND_IRREVERSIBLE=yes \
 *   node scripts/secure_sweep.cjs --to 0xLEDGER --broadcast
 *
 * Note: ERC-20 transfers cost gas — the hot wallet needs enough ETH first.
 *       LP positions (Aerodrome) must be withdrawn via the router separately;
 *       this script handles native ETH + ERC-20 balances only.
 */
const { ethers } = require('ethers');

const RPC = process.env.BASE_MAINNET_RPC || process.env.BASE_RPC_URL || 'https://mainnet.base.org';

const DEFAULT_TOKENS = {
  QFLOP: '0xa8F5e136aa74803B8DB377a14f79F6c8Dd3959c7',
  wQFLOP: '0x69262A2D7c92c074729823B654fE7E4Cdb749747',
  WETH: '0x4200000000000000000000000000000000000006',
};

const ERC20_ABI = [
  'function balanceOf(address) view returns (uint256)',
  'function decimals() view returns (uint8)',
  'function transfer(address to, uint256 amount) returns (bool)',
];

function parseArgs(argv) {
  const a = { broadcast: false, to: null, from: null, tokens: Object.values(DEFAULT_TOKENS) };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--broadcast') a.broadcast = true;
    else if (argv[i] === '--to') a.to = argv[++i];
    else if (argv[i] === '--from') a.from = argv[++i];
    else if (argv[i] === '--tokens') a.tokens = argv[++i].split(',').map((s) => s.trim());
  }
  return a;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const provider = new ethers.JsonRpcProvider(RPC);

  if (!args.to || !/^0x[0-9a-fA-F]{40}$/.test(args.to)) {
    console.error('ERROR: --to <destination address> is required (your Ledger/Safe).');
    process.exit(2);
  }
  const dest = ethers.getAddress(args.to);

  // Resolve the source. Broadcast derives it from the key; dry-run can use --from.
  let signer = null;
  let from;
  const rawKey = process.env.ETH_PRIVATE_KEY || process.env.BASE_PRIVATE_KEY || '';
  if (/^0x[0-9a-fA-F]{64}$/.test(rawKey)) {
    signer = new ethers.Wallet(rawKey, provider);
    from = await signer.getAddress();
  } else if (args.from && /^0x[0-9a-fA-F]{40}$/.test(args.from)) {
    from = ethers.getAddress(args.from);
  } else {
    console.error('ERROR: provide --from <addr> for dry-run, or set ETH_PRIVATE_KEY to broadcast.');
    process.exit(2);
  }

  const net = await provider.getNetwork();
  console.log(`RPC ${RPC} chainId ${net.chainId}`);
  console.log(`FROM ${from}`);
  console.log(`TO   ${dest}`);
  console.log(`MODE ${args.broadcast ? 'BROADCAST' : 'DRY-RUN'}\n`);

  if (from.toLowerCase() === dest.toLowerCase()) {
    console.error('ERROR: source and destination are identical. Aborting.');
    process.exit(2);
  }

  const feeData = await provider.getFeeData();
  const gasPrice = feeData.maxFeePerGas || feeData.gasPrice || 0n;
  const plan = [];

  // ERC-20 balances first (these need gas to move).
  for (const addr of args.tokens) {
    if (!/^0x[0-9a-fA-F]{40}$/.test(addr)) continue;
    try {
      const c = new ethers.Contract(addr, ERC20_ABI, provider);
      const [bal, dec] = await Promise.all([c.balanceOf(from), c.decimals().catch(() => 18)]);
      if (bal > 0n) {
        let gas = 65000n;
        try { gas = await c.transfer.estimateGas(dest, bal, { from }); } catch { /* keep default */ }
        plan.push({ kind: 'ERC20', token: addr, amount: bal.toString(), human: ethers.formatUnits(bal, dec), gas });
      }
    } catch (e) {
      console.log(`  (skip ${addr}: ${e.shortMessage || e.message})`);
    }
  }

  // Native ETH last — sweep balance minus a gas reserve for the ERC-20 txs above.
  const ethBal = await provider.getBalance(from);
  const erc20GasCost = plan.reduce((s, p) => s + (p.gas || 0n), 0n) * gasPrice;
  const ethTransferGas = 21000n;
  const reserve = erc20GasCost + ethTransferGas * gasPrice;
  const ethToSend = ethBal > reserve ? ethBal - reserve : 0n;

  console.log('PLANNED TRANSFERS:');
  for (const p of plan) console.log(`  ERC20 ${p.human}  (${p.token})  ~gas ${p.gas}`);
  console.log(`  ETH   ${ethers.formatEther(ethToSend)} (after gas reserve ${ethers.formatEther(reserve)})`);

  // Sufficiency check — the classic trap: tokens present, no gas to move them.
  if (plan.length > 0 && ethBal < erc20GasCost) {
    console.log(`\n⚠️  INSUFFICIENT GAS: holding ${plan.length} token balance(s) but only ` +
      `${ethers.formatEther(ethBal)} ETH; need ~${ethers.formatEther(erc20GasCost)} ETH to move them. ` +
      `Fund ${from} with a little ETH first.`);
  }

  if (!args.broadcast) {
    console.log('\nDRY-RUN complete. Nothing sent. Re-run with --broadcast (and the safety env) to execute.');
    return;
  }

  // ── BROADCAST PATH (gated; intended to be run by the asset owner only) ──
  if (process.env.I_UNDERSTAND_IRREVERSIBLE !== 'yes') {
    console.error('\nREFUSED: --broadcast requires env I_UNDERSTAND_IRREVERSIBLE=yes. ' +
      'These transfers are irreversible. Aborting.');
    process.exit(1);
  }
  if (!signer) {
    console.error('REFUSED: no signing key in env. Set ETH_PRIVATE_KEY to broadcast.');
    process.exit(1);
  }

  for (const p of plan) {
    const c = new ethers.Contract(p.token, ERC20_ABI, signer);
    const tx = await c.transfer(dest, BigInt(p.amount));
    console.log(`  sent ERC20 ${p.human} (${p.token}) tx ${tx.hash}`);
    await tx.wait();
  }
  if (ethToSend > 0n) {
    const tx = await signer.sendTransaction({ to: dest, value: ethToSend });
    console.log(`  sent ETH ${ethers.formatEther(ethToSend)} tx ${tx.hash}`);
    await tx.wait();
  }
  console.log('\nSweep complete. Verify on BaseScan, then retire the old key.');
}

main().catch((e) => { console.error(e); process.exit(1); });
