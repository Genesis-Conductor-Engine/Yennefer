#!/usr/bin/env node
/**
 * READ-ONLY asset inventory for a Base address.
 * No private key, no signing, no transactions. Safe to run anytime.
 *
 * Usage:
 *   node scripts/inventory.cjs 0xWALLET [0xWALLET2 ...]
 *   BASE_RPC_URL=https://... node scripts/inventory.cjs 0xWALLET
 */
const { ethers } = require('ethers');

const RPC = process.env.BASE_MAINNET_RPC || process.env.BASE_RPC_URL || 'https://mainnet.base.org';

// Known Base tokens/positions to probe. Extend freely.
const TOKENS = [
  { sym: 'QFLOP', addr: '0xa8F5e136aa74803B8DB377a14f79F6c8Dd3959c7' },
  { sym: 'wQFLOP', addr: '0x69262A2D7c92c074729823B654fE7E4Cdb749747' },
  { sym: 'WETH', addr: '0x4200000000000000000000000000000000000006' },
  { sym: 'AERO-LP(wQFLOP/WETH)', addr: '0x4aBC6D796cd036b6f1E433A97F9784a00f90C53e' },
];

const ERC20_ABI = [
  'function balanceOf(address) view returns (uint256)',
  'function decimals() view returns (uint8)',
  'function symbol() view returns (string)',
];

async function inventory(provider, address) {
  console.log(`\n=== ${address} ===`);
  const eth = await provider.getBalance(address);
  console.log(`  ETH: ${ethers.formatEther(eth)}`);

  for (const t of TOKENS) {
    try {
      const c = new ethers.Contract(t.addr, ERC20_ABI, provider);
      const [bal, dec] = await Promise.all([c.balanceOf(address), c.decimals().catch(() => 18)]);
      const human = ethers.formatUnits(bal, dec);
      const flag = bal > 0n ? '  <-- nonzero' : '';
      console.log(`  ${t.sym} (${t.addr}): ${human}${flag}`);
    } catch (e) {
      console.log(`  ${t.sym} (${t.addr}): <read error: ${e.shortMessage || e.message}>`);
    }
  }
}

async function main() {
  const targets = process.argv.slice(2);
  if (targets.length === 0) {
    console.error('usage: node scripts/inventory.cjs 0xWALLET [0xWALLET2 ...]');
    process.exit(2);
  }
  const provider = new ethers.JsonRpcProvider(RPC);
  const net = await provider.getNetwork();
  console.log(`RPC: ${RPC}  chainId: ${net.chainId}`);
  for (const addr of targets) {
    if (!/^0x[0-9a-fA-F]{40}$/.test(addr)) {
      console.log(`\n=== ${addr} ===\n  SKIP: not a valid address`);
      continue;
    }
    await inventory(provider, ethers.getAddress(addr));
  }
  console.log('\n(read-only — no transactions sent)');
}

main().catch((e) => { console.error(e); process.exit(1); });
