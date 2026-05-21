#!/usr/bin/env node
/**
 * B4 — prep_eis_deploy: build constructor calldata + predicted address for
 * EulersIdentitySynthesis(treasurySink = SAFE_ADDRESS). DOES NOT broadcast.
 *
 * Reads compiled bytecode/abi from the Hardhat artifact. If the artifact is
 * absent (contract not added/compiled), emits a TODO and exits non-zero — it
 * NEVER fabricates bytecode.
 *
 * Env:
 *   SAFE_ADDRESS (required)         — treasurySink
 *   DEPLOYER_ADDRESS (required)     — for CREATE nonce / CREATE2 deployer
 *   SALT (optional, 0x..32 bytes)   — if set, computes CREATE2 address
 *   BASE_MAINNET_RPC|BASE_RPC_URL   — optional
 */
const fs = require('node:fs');
const path = require('node:path');
const { ethers } = require('ethers');

const RPC = process.env.BASE_MAINNET_RPC || process.env.BASE_RPC_URL || 'https://mainnet.base.org';
const ARTIFACT = path.join(process.cwd(),
  'artifacts/contracts/EulersIdentitySynthesis.sol/EulersIdentitySynthesis.json');
const ts = () => new Date().toISOString();
const out = (o) => process.stdout.write(JSON.stringify({ ...o, ts: ts() }) + '\n');
function fail(reason, todo) {
  out({ step: 'prep_eis_deploy', ok: false, reason, ...(todo ? { todo } : {}) });
  process.exit(1);
}

async function main() {
  const safe = process.env.SAFE_ADDRESS;
  const deployer = process.env.DEPLOYER_ADDRESS;
  if (!safe || !/^0x[0-9a-fA-F]{40}$/.test(safe)) fail('SAFE_ADDRESS unset/malformed');
  if (!deployer || !/^0x[0-9a-fA-F]{40}$/.test(deployer)) fail('DEPLOYER_ADDRESS unset/malformed');

  if (!fs.existsSync(ARTIFACT)) {
    return fail('EIS artifact not found — contract absent or not compiled',
      `add the real contracts/EulersIdentitySynthesis.sol (see patches/eis-immutable-sink.patch), then: npx hardhat compile  ->  produces ${path.relative(process.cwd(), ARTIFACT)}`);
  }

  const artifact = JSON.parse(fs.readFileSync(ARTIFACT, 'utf8'));
  const iface = new ethers.Interface(artifact.abi);
  const bytecode = artifact.bytecode;
  if (!bytecode || bytecode === '0x') fail('artifact has empty bytecode');

  // constructor(address sink) — encode SAFE_ADDRESS as the treasurySink arg.
  let ctorArgs;
  try { ctorArgs = iface.encodeDeploy([ethers.getAddress(safe)]); }
  catch (e) { return fail(`constructor encode failed (check ABI): ${e.message}`); }
  const initCode = ethers.concat([bytecode, ctorArgs]);
  const bytecodeHash = ethers.keccak256(initCode);

  let predictedAddress, salt = null, mode;
  if (process.env.SALT) {
    salt = process.env.SALT;
    if (!/^0x[0-9a-fA-F]{64}$/.test(salt)) fail('SALT must be 0x + 32 bytes');
    predictedAddress = ethers.getCreate2Address(ethers.getAddress(deployer), salt, bytecodeHash);
    mode = 'CREATE2';
  } else {
    const provider = new ethers.JsonRpcProvider(RPC);
    const nonce = await provider.getTransactionCount(ethers.getAddress(deployer)).catch(() => null);
    if (nonce === null) fail('could not read deployer nonce from RPC (set SALT for CREATE2 instead)');
    predictedAddress = ethers.getCreateAddress({ from: ethers.getAddress(deployer), nonce });
    mode = `CREATE(nonce=${nonce})`;
  }

  // Best-effort gas estimate (won't revert the prep if RPC declines).
  let gasEstimate = null;
  try {
    const provider = new ethers.JsonRpcProvider(RPC);
    gasEstimate = (await provider.estimateGas({ from: ethers.getAddress(deployer), data: initCode })).toString();
  } catch { /* leave null */ }

  const plan = {
    deployer: ethers.getAddress(deployer),
    treasurySink: ethers.getAddress(safe),
    mode, salt, bytecodeHash, predictedAddress, gasEstimate,
    constructorCalldata: ctorArgs,
  };
  fs.mkdirSync(path.join(process.cwd(), 'out'), { recursive: true });
  fs.writeFileSync(path.join(process.cwd(), 'out', 'eis_deploy_plan.json'), JSON.stringify(plan, null, 2));

  // Commands for Igor to run with his Ledger (NOT executed here).
  process.stderr.write('\n== Deploy with Ledger (run yourself; review on device) ==\n');
  process.stderr.write(`# hardhat (uses ledgerAccounts from hardhat.config.cjs):\n`);
  process.stderr.write(`SAFE_ADDRESS=${safe} npx hardhat run scripts/deploy_eis.cjs --network baseMainnet\n`);
  process.stderr.write(`# or cast (Foundry) with a Ledger:\n`);
  process.stderr.write(`cast send --ledger --rpc-url "$BASE_MAINNET_RPC" --create ${ethers.hexlify(initCode)}\n`);

  out({ step: 'prep_eis_deploy', ok: true, mode, treasurySink: plan.treasurySink,
    predictedAddress, bytecodeHash, gasEstimate });
}

main().catch((e) => fail(e.message));
