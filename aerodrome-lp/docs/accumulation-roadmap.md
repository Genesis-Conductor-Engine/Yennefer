# Liquid Funds Accumulation Roadmap
**Assessed:** 2026-06-27 | **Target:** 250 ETH (Genesis Conductor Phase III)

## Current State (on-chain truth)

| Asset | Value | Notes |
|---|---|---|
| Pool TVL | ~$1.01 | DEGENERATE — WETH reserve 0.000144 ETH |
| Primary LP position | 98.3% of pool | ~5,355 LP tokens; $0.99 today |
| Legacy Minter ETH | 0.000061 ETH | ~$0.21 — gas only |
| MPCVAULT ETH | 0.000000 ETH | Empty |
| wQFLOP in Legacy | ~0 wQFLOP | Dust amount |
| Gauge | ❌ None | No AERO emissions |
| Daily cap unused | 0.1 ETH / day | Ready when funded |

## The $3 unlock

The pool needs **0.000856 ETH more WETH** ($2.997) to cross the degenerate threshold.
Once crossed, the workflow switches from HOLD to ADD — proportional liquidity can be
added productively up to the per-tx cap (0.02 ETH) / daily cap (0.1 ETH).

**To execute:**
1. Get 0.01 ETH minimum onto the LP_OWNER wallet (covers add + gas margin)
2. Wrap to WETH via the WETH contract (`deposit()` payable)
3. `touch ~/Yennefer/aerodrome-lp/.ARMED`
4. `LP_OWNER=<wallet> SIGNER_ACCOUNT=<alias> bash workflow.sh --live --max-weth 0.002`

## Revenue streams — live today

### 1. Delta Truth Engine API (delta.genesisconductor.io)
- `/api/verify` — deterministic RTPTPA verification (KV-cached)
- `/api/anchor` — on-chain-ready D1 ledger commit
- `/api/anchor/onchain` — CDP wallet proof tx to Base chain
- **Monetization path:** Add API key tier (x-api-key header, KV usage tracking)
  - Free: 100 verifies/day
  - Pro: $9.99/mo → unlimited verify + anchor
  - Proof tier: $0.50/anchor (on-chain tx via CDP wallet)

### 2. Yennefer Subscriptions (yennefer.quest — portal up, Stripe handler offline)
| Tier | MRR potential |
|---|---|
| Observer ($0) | leads |
| Participant ($9.99/mo) | $100 → $1,000 MRR |
| Collaborator ($49.99/mo) | $500 → $5,000 MRR |
| Architect ($199.99/mo) | $2,000 → $20,000 MRR |

**Action:** Restart Stripe handler → immediate revenue on existing portal

### 3. Aerodrome LP (once funded + gauge)
Pool fee: 0.3% on volume. With a gauge (AERO emissions):
- $1K TVL, $10K/day volume → ~$30/day fees + AERO
- $10K TVL, $100K/day volume → ~$300/day + AERO
- 98.3% LP share passes most of this to the primary LP

### 4. CDP On-chain Anchoring
Once CDP credentials are configured (`cdp/.env`):
- `delta-truth-anchor` wallet auto-funds from faucet (testnet) / real ETH (mainnet)
- Anchor tx calldata proves truth claims on-chain permanently
- Chargeable: $0.50-1.00 per anchor

## Phased accumulation path

### Phase 0 — Unlock (this week, cost ~$5-10)
- [ ] Fund LP_OWNER wallet with 0.01 ETH on Base
- [ ] Run `workflow.sh --live --max-weth 0.002` to add first productive liquidity
- [ ] Pool crosses degenerate threshold → daily automated adds begin

### Phase 1 — First Revenue (weeks 1-4)
- [ ] Restart Stripe handler (systemctl start yennefer-stripe.service)
- [ ] Add API key tier to Delta Truth `/api/verify` (KV-tracked, ~1 day of work)
- [ ] Fill `cdp/.env` → first on-chain anchors live
- [ ] Target: $100-500 MRR

### Phase 2 — Aerodrome Gauge (month 1-3)
- [ ] Submit gauge proposal to governance.aerodrome.finance (template ready at docs/gauge-proposal.md)
- [ ] Accumulate veAERO votes via community outreach
- [ ] Once gauge approved: LP fee + AERO compound automatically
- [ ] Target: $1K-10K TVL in pool

### Phase 3 — Scale (month 3-12)
- [ ] Delta Truth Pro tier live → 50 subscribers → $500/mo
- [ ] Pool TVL $10K+ → meaningful fee APR
- [ ] AERO emissions re-LP into pool (compounding)
- [ ] Target: 1 ETH in pool, $2K MRR

### Phase 4 — Goal (12-24 months)
- [ ] Stripe MRR $10K+ → convert to ETH → add to LP
- [ ] CDP anchoring volume → ETH accumulation
- [ ] Pool TVL 10+ ETH → AERO compound meaningful
- [ ] Target: **250 ETH** (pool + treasury)

## ETH/WETH acquisition paths (no CEX needed)

1. **CDP faucet** (testnet only — for anchor validation): zero cost
2. **Base bridge** (Ethereum mainnet → Base): standard Ethereum Bridge
3. **Aerodrome swap** (once pool live): swap earned AERO → WETH
4. **Stripe revenue** → ETH (via Coinbase onramp or bridge)
5. **CDP mainnet wallet** — accept ETH payments for Delta Truth Pro

## Monitor

```bash
# One-shot check
bash ~/Yennefer/aerodrome-lp/monitor.sh

# Add to crontab (every 5 min)
*/5 * * * * bash ~/Yennefer/aerodrome-lp/monitor.sh >> ~/Yennefer/aerodrome-lp/logs/monitor.log 2>&1
# Alert when status changes to HEALTHY (pool funded)
```

## Gauge submission URLs
- Aerodrome governance forum: https://governance.aerodrome.finance
- Calldata for governor: see docs/gauge-proposal.md
- Aerodrome Discord: https://discord.gg/aerodrome (post in #gauge-proposals)
