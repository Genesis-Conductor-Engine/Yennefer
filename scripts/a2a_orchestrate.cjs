#!/usr/bin/env node
/**
 * C1 — a2a_orchestrate: single entry point running every READ-ONLY / DRY-RUN
 * step in dependency order. No flag combination here can broadcast — each
 * broadcast remains a separate, manually-gated, owner-run command.
 *
 * Order: verify_safe -> inventory -> secure_sweep(dry) -> lp_unwind(dry) -> prep_eis_deploy
 * Output: one JSONL line per step to out/a2a_run_<ISO_TS>.jsonl, final a2a_summary line.
 * On any non-OK step: abort the rest, still emit the summary with the failure reason.
 *
 * Env: SAFE_ADDRESS (required), FROM_ADDRESS (default 0x9545…6956),
 *      POOL_ADDRESS (for lp_unwind), DEPLOYER_ADDRESS (for prep_eis_deploy), RPC.
 */
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

const ts = () => new Date().toISOString();
const FROM = process.env.FROM_ADDRESS || '0x9545e2439c5c75d3aA723AcaC1AA6B0fa1DB6956';
const SAFE = process.env.SAFE_ADDRESS || '';

const runDir = path.join(process.cwd(), 'out');
fs.mkdirSync(runDir, { recursive: true });
fs.mkdirSync(path.join(process.cwd(), '.yennefer-cache'), { recursive: true });
const runFile = path.join(runDir, `a2a_run_${ts().replace(/[:.]/g, '-')}.jsonl`);
const append = (obj) => fs.appendFileSync(runFile, JSON.stringify(obj) + '\n');

function lastJsonLine(text) {
  const lines = String(text || '').trim().split('\n').filter(Boolean);
  for (let i = lines.length - 1; i >= 0; i--) {
    try { return JSON.parse(lines[i]); } catch { /* not json */ }
  }
  return null;
}

// Run a child step; returns {ok, line}. Never throws.
function runStep(name, file, args, extraEnv, cacheTo) {
  const env = { ...process.env, ...extraEnv };
  let stdout = '', ok = false;
  try {
    stdout = execFileSync('node', [file, ...args], { env, encoding: 'utf8', stdio: ['ignore', 'pipe', 'inherit'] });
    ok = true;
  } catch (e) {
    stdout = (e.stdout || '').toString();
    ok = false;
  }
  if (cacheTo) {
    try { fs.writeFileSync(cacheTo, JSON.stringify({ step: name, raw: stdout, ts: ts() }, null, 2)); } catch { /* ignore */ }
  }
  const emitted = lastJsonLine(stdout);
  const line = emitted && emitted.step
    ? { ...emitted, ok: emitted.ok !== undefined ? emitted.ok : ok }
    : { step: name, ok, ts: ts() };
  append(line);
  return { ok: line.ok === true, line };
}

function summarize(steps, ok, nextActions, failReason) {
  const summary = {
    step: 'a2a_summary', ok, ts: ts(),
    run_file: path.relative(process.cwd(), runFile),
    steps: steps.map((s) => ({ step: s.line.step, ok: s.ok })),
    next_actions: nextActions,
    ...(failReason ? { fail_reason: failReason } : {}),
  };
  append(summary);
  process.stdout.write(JSON.stringify(summary) + '\n');
  process.exit(ok ? 0 : 1);
}

function main() {
  if (!SAFE || !/^0x[0-9a-fA-F]{40}$/.test(SAFE)) {
    append({ step: 'a2a_preflight', ok: false, ts: ts(), reason: 'SAFE_ADDRESS unset/malformed' });
    return summarize([], false, ['Deploy the Safe (docs/safe-setup.md), then export SAFE_ADDRESS'], 'SAFE_ADDRESS unset');
  }

  const cacheDir = path.join(process.cwd(), '.yennefer-cache');
  const steps = [];

  // 1. verify_safe — gate for everything downstream.
  const vs = runStep('verify_safe', 'scripts/verify_safe.cjs', [], { SAFE_ADDRESS: SAFE });
  steps.push(vs);
  if (!vs.ok) {
    return summarize(steps, false,
      ['Safe failed verification — confirm it is deployed on Base (chainId 8453), 2-of-3, via docs/safe-setup.md, then re-run'],
      'verify_safe failed');
  }

  // 2. inventory (read-only) — source wallet holdings.
  steps.push(runStep('inventory', 'scripts/inventory.cjs', [FROM], {}, path.join(cacheDir, 'inventory.json')));

  // 3. secure_sweep dry-run -> Safe.
  steps.push(runStep('secure_sweep', 'scripts/secure_sweep.cjs', ['--to', SAFE, '--from', FROM], {}));

  // 4. lp_unwind dry-run -> Safe.
  steps.push(runStep('lp_unwind', 'scripts/lp_unwind.cjs', [], { SAFE_ADDRESS: SAFE, TO_ADDRESS: SAFE, FROM_ADDRESS: FROM }));

  // 5. prep_eis_deploy (treasurySink = Safe).
  steps.push(runStep('prep_eis_deploy', 'scripts/prep_eis_deploy.cjs', [], { SAFE_ADDRESS: SAFE }));

  const allOk = steps.every((s) => s.ok);
  const nextActions = [];
  if (!steps.find((s) => s.line.step === 'lp_unwind')?.ok) {
    nextActions.push('Set POOL_ADDRESS to the real Aerodrome LP token (not the router) and re-run lp_unwind');
  }
  if (!steps.find((s) => s.line.step === 'prep_eis_deploy')?.ok) {
    nextActions.push('Add+compile EulersIdentitySynthesis (git apply patches/eis-immutable-sink.patch; npx hardhat compile), set DEPLOYER_ADDRESS');
  }
  nextActions.push('Review out/*.json plans; run each broadcast manually with your Ledger + the per-script gate');

  summarize(steps, allOk, nextActions, allOk ? null : 'one or more dry-run steps reported not-ok');
}

main();
