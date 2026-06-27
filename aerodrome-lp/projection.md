# wQFLOP Liquidity — Plans & Projections (2026-06-27)

## Pool State
- **Pool:** `0x4aBC6D796cd036b6f1E433A97F9784a00f90C53e` (Aerodrome volatile, Base)
- **Reserves:** WETH = 0.000144 ETH | wQFLOP = 206,447,530,318 wQFLOP
- **Price:** ~696 wei per wQFLOP (~$0.0000000024)
- **TVL:** ~$1.01 | **Degenerate:** YES | **Gauge:** None (no AERO emissions)

## Decision: HOLD
**Reason:** `pool_degenerate_weth_dust` — WETH reserve (0.000144 ETH) below minimum (0.001 ETH)

## The $3 Unlock
Pool needs **0.000856 ETH more** ($2.997) to clear the degenerate threshold.
Once cleared, the workflow switches ADD → daily automated LP adds (cap: 0.1 ETH/day, 0.02 ETH/tx).

**LP position:** ~5,355 LP tokens = **98.3% of pool** (primary wallet)

## Daily Cap
Used: 0 / 100,000,000,000,000,000 wei (cap unused — wallet unfunded)

## Accumulation Phase: Phase 0 — Pool Unlock
**Immediate unlock cost: ~$35** (0.01 ETH covers add + gas margin)

## Revenue Streams
| Stream | Status | Notes |
|---|---|---|
| Delta Truth API | ✅ Live, unmonetized | delta.genesisconductor.io/api/* |
| CDP On-chain Anchoring | 🔧 Built, pending credentials | cdp/.env needs CDP keys |
| Yennefer Subscriptions | ⚠️ Portal up, Stripe offline | restart yennefer-stripe.service |
| Aerodrome LP fees | 💤 ~0% at $1 TVL | grows once pool is funded |

## Forward Projection
| Phase | Action | Cost | Milestone |
|---|---|---|---|
| 0 | Fund LP_OWNER → un-degenerate pool | $35 | Daily LP adds begin |
| 1 | Stripe online + Delta Truth Pro tier | $0 | $500 MRR |
| 2 | Aerodrome gauge approved | governance vote | AERO emissions begin |
| 3 | $10K TVL in pool | ~$5K WETH | Meaningful fee APR |
| 4 | 250 ETH target | 12-24 months | Genesis Conductor Phase III |

## Next Actions
1. 🔴 Fund LP_OWNER wallet with 0.01 ETH on Base (~$35)
2. 🔴 Register `ANCHOR_RELAY_KEY` Pages secret (see `~/delta/cdp/README.md`)
3. 🟡 Fill `cdp/.env` CDP credentials → on-chain anchors live
4. 🟡 `sudo systemctl restart yennefer-stripe.service` → Stripe revenue
5. 🟡 Submit Aerodrome gauge proposal (template: `docs/gauge-proposal.md`)
6. ⬜ Add API key tier to Delta Truth `/api/verify` (1 day build)

## Monitor
Pool health auto-monitored every 5 min via `monitor.sh`.
Current: `DEGENERATE+GAUGE_MISSING` — pool will self-report when threshold crossed.
