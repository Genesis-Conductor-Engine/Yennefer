# QFLOP / wQFLOP Recovery Workflow — Accrue 1 ETH

**Status:** ACTIVE (dry-run / monitor until gas + live signer)  
**Goal:** Accrue **1.0 ETH equivalent** (wallet ETH + WETH + LP share of pool WETH), then hand off to vibe agent `/loop n=n`.  
**Assessed:** 2026-07-08T23:49Z UTC  
**Repo:** `Genesis-Conductor-Engine/Yennefer` · branch `feat/yennefer-safe-rotation`  
**Harness:** `~/Yennefer/aerodrome-lp` + `~/Yennefer/qflop-backfill`

---

## Onchain truth (live snapshot)

| Item | Value |
|------|--------|
| Chain | Base mainnet (8453) |
| LP_OWNER | `0x60C4499870f115664d7FfD8411b023DBEf3377d9` |
| Pool (volatile) | `0x4aBC6D796cd036b6f1E433A97F9784a00f90C53e` |
| wQFLOP | `0x69262A2D7c92c074729823B654fE7E4Cdb749747` |
| WETH | `0x4200000000000000000000000000000000000006` |
| Pool WETH reserve | ~0.003904 ETH |
| LP share | **99.7371%** (~34903.63 / 34995.64 LP) |
| Accrued ETH-eq | **~0.003896 ETH** (~**0.39%** of 1 ETH goal) |
| Wallet ETH | ~0.00000166 (below gas floor ~0.000003) |
| Wallet WETH | dust (~6.4e-11) |
| Wallet wQFLOP | ~9.09e8 |
| Gauge | **none** (`0x0`) — fees only, no AERO |
| Decision (workflow) | **ADD** (`within_caps`) but live blocked by gas / no `PRIVATE_KEY` |
| Pool status | `HEALTHY+GAUGE_MISSING` (WETH ≥ 0.001 threshold) |

**Primary blocker for live execution:** LP_OWNER has insufficient ETH for gas (~1.66e-6 ETH; need ≥ ~3e-6 for intrinsic tx, prefer ≥ 0.01 ETH operational buffer).

---

## Active processes (must stay online)

| Process | Manager | Mode | Purpose |
|---------|---------|------|---------|
| `qflop-backfill` | pm2 | online | Multi-wallet wrap/backfill orchestrator |
| `qflop-recovery-dashboard` | pm2 | online | Recovery dashboard |
| `lp-autoscale` | pm2 | online **dry-run** | 30m cycle: assess, quote swap+LP, write `/dev/shm/lp_dashboard.json` + goal % |
| `lp-dashboard` | pm2 | online | Propagate LP dashboard |
| `qflop-here-realtime` | pm2 | online | here.now live publish |
| `cdp-wallet-manager` | pm2 | online | CDP wallet ops |
| heartbeat.sh | cron `15 */4` | active | HTML heartbeat |
| asset_transmute.mjs | cron `0 */2` | dry-run | LP→ETH transmute scan |
| wqflop_monitor.py | cron `*/15` | active | Signal monitor |
| `.ARMED` | file present | gated | Live forge adds require this + funded wallet |

Restart fleet:

```bash
export PATH="$HOME/.npm-global/bin:$PATH"
pm2 start ~/Yennefer/qflop-backfill/ecosystem.config.cjs
pm2 start ~/Yennefer/aerodrome-lp/ecosystem.config.cjs
pm2 save
```

---

## Loop until 1 ETH (`/loop n=n`)

Each iteration (vibe agent or operator):

1. **ASSESS**  
   `LP_OWNER=0x60C4… bash ~/Yennefer/aerodrome-lp/workflow.sh --status`  
   and/or read `/dev/shm/lp_dashboard.json` → `goal.accrued_eth_eq`, `goal.progress_pct`.

2. **FUND GAS (if ETH < 0.003)**  
   Send ≥ **0.01 ETH** on Base to `LP_OWNER`. Without this, all live swaps/adds fail.

3. **DECIDE**  
   - If `goal.accrued_eth_eq >= 1.0` → **EXIT loop**, document milestone, handoff complete.  
   - If pool healthy + funded + `decision=ADD` → simulate then live add (capped).  
   - Else HOLD / dry-run; re-check funding and revenue paths.

4. **SIMULATE**  
   `LP_OWNER=… bash workflow.sh --dry-run`  
   Require forge output containing `LP minted` before any broadcast.

5. **EXECUTE (live)** — only when all hold:  
   - `.ARMED` exists  
   - `SIGNER_ACCOUNT=qflop-lp` (foundry keystore) **or** `PRIVATE_KEY` in env  
   - within `config/caps.json` (0.02 WETH/tx, 0.1 WETH/day)  
   ```bash
   set -a; source ~/Yennefer/aerodrome-lp/.env; set +a
   SIGNER_ACCOUNT=qflop-lp LP_OWNER=0x60C4499870f115664d7FfD8411b023DBEf3377d9 \
     bash ~/Yennefer/aerodrome-lp/workflow.sh --live --max-weth 0.002
   ```

6. **RECORD**  
   - `projections.json` + `projection.md`  
   - append goal progress to this doc or `/dev/shm/lp_dashboard.json`  
   - optional Notion page: *wQFLOP Liquidity — Plans & Projections*

7. **SLEEP / next n**  
   Autoscale interval 30m; heartbeat every 4h; transmute dry-run every 2h.

### Accrual formula (ETH-eq)

```
accrued = wallet_ETH + wallet_WETH + (pool_WETH_reserve × lp_balance / total_supply)
goal_met = accrued >= 1.0
```

wQFLOP inventory is **not** counted as ETH-eq until swapped (thin pool → tiny WETH out per cycle).

---

## Compiler policy (explorer bug warnings)

Use **Solc 0.8.32** everywhere for new compiles / re-verification:

| Bug | Severity | Fixed in |
|-----|----------|----------|
| LostStorageArrayWriteOnSlotOverflow | low | **0.8.32** |
| VerbatimInvalidDeduplication | low | 0.8.23 |
| FullInlinerNonExpressionSplitArgumentEvaluationOrder | low | 0.8.21 |
| MissingSideEffectsOnSelectorAccess | low | 0.8.21 |

Config: `aerodrome-lp/foundry.toml` (`solc = "0.8.32"`), root `hardhat.config.cjs`, contract pragmas `^0.8.32`.

**Note:** Already-verified BaseScan contracts keep old warnings until **redeploy + re-verify** with 0.8.32. Local forge/hardhat builds are clean on 0.8.32.

```bash
export PATH="$HOME/.foundry/bin:$PATH"
cd ~/Yennefer/aerodrome-lp && forge build
cd ~/Yennefer && npx hardhat clean && npx hardhat compile
```

---

## Revenue / unlock paths (toward 1 ETH)

1. **Fund LP_OWNER** 0.01+ ETH → enable live autoscale + capped ADD.  
2. **Swap fees** on 99.7% LP share (no gauge → no AERO).  
3. **qflop-backfill** synthetic/meter stream (Stripe unset → cashout blocked).  
4. **Gauge proposal** (`docs/gauge-proposal.md`) when TVL justifies emissions.  
5. **Do not** force-seed degenerate ratios; pool is currently non-degenerate.

---

## Vibe agent handoff checklist

- [x] Compiler pinned to 0.8.32; rebuilds clean  
- [x] LP + backfill pm2 apps online; autoscale dry-run writing goal progress  
- [x] Workflow doc (this file)  
- [ ] Operator: fund `LP_OWNER` ≥ 0.01 ETH on Base  
- [ ] Operator: export `PRIVATE_KEY` for pm2 live **or** use interactive `SIGNER_ACCOUNT=qflop-lp`  
- [ ] Continue `/loop n=n` until `goal.accrued_eth_eq >= 1.0`  
- [ ] At 1 ETH: tag release, update Notion, freeze dry-run policy if desired  

**Subagent:** `aerodrome-qflop-lp` (`~/.claude/agents/aerodrome-qflop-lp.md`)  
**Guardrails:** no raw keys in logs; sim-first; caps law; `.ARMED` for live.
