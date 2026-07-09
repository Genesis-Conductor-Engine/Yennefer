# Onchain / Agent Instrument Inventory (ground truth)

**Audited:** 2026-07-08T23:59Z UTC  
**Method:** Prior agentic session findings + live RPC multi-chain + local registries + Notion worker config  
**Notion `ntn`:** blocked — `NOTION_API_TOKEN` / `NOTION_TOKEN` are placeholders (`your-notion-…` / unexpanded `${NOTION…}`); diamondvault worker has empty token; worker still healthy on :8081 with null contracts.

---

## Executive verdict

| Claim | Verdict |
|-------|---------|
| $15k–$20k spendable treasury across instruments | **NOT FOUND onchain under controlled keys** |
| Polygon agents hold liquid funds | **NO** — 0 POL on controlled addresses; QFLOP/wQFLOP **not deployed** on Polygon |
| Aerodrome is a deep treasury | **NO** — thin Base pool only (~0.0028 WETH depth, mostly self-owned LP) |
| Hardhat holds production funds | **NO** — config only; hot key = LP_OWNER; Ledger optional empty |
| `/dev/shm` ~$1.7M liquidity | **SYNTHETIC / NON-SPENDABLE** (prior agents already flagged as fabricated vs onchain) |

**Spendable total (controlled keys):** ≈ **0.00127 ETH** (~**$2.21** @ $1,742/ETH) across Base.

---

## Prior agentic sessions (already established)

From fleet audit language recovered in workspace (multichain liquid accelerant review):

> LP owner holds **~0.00163 ETH (~$4)**; Aerodrome pool **~0.004 WETH (~$15)** depth and **~99.7% self-owned**. Local ledger asserting **~$1.79M "real" liquidity** is **physically impossible** vs onchain and is **not launch-ready**.  
> **Polygon (137): NO-GO (VAPOR)** — no token, no pool, no chain config for QFLOP/wQFLOP.  
> Same for Optimism as a QFLOP venue.

This session re-verified those conclusions with live RPC (see below). Gas bootstrap since then raised LP_OWNER to **~0.00120 ETH**.

---

## Instrument matrix

| Instrument | Status | Chain | Liquid under keys | Notes |
|------------|--------|-------|-------------------|-------|
| **LP_OWNER** `0x60C4…77d9` | LIVE | Base | **~0.00120 ETH** | = `PRIVATE_KEY` wallet; gas-keeper target |
| **HD agent wallets 0–24** (mnemonic + builder codes) | LIVE addresses | Base | dust on 0,1 only (~0.00007) | same set as `wallet_builder_codes.json` |
| **HD on Polygon / OP / Arb** | empty | 137 / 10 / 42161 | **0** | checked LP + hd0 + hd1 |
| **Aerodrome wQFLOP/WETH** `0x4aBC…C53e` | LIVE pool | Base | ~0.0028 WETH TVL | no gauge; LP ~99.6% self-owned after harvests |
| **Aerodrome (other chains)** | N/A | — | — | no configured pools |
| **Hardhat** | TOOLING | Base / Sepolia | none separate | `HOT_ACCOUNTS` = same LP key; Ledger unset |
| **Foundry keystore `qflop-lp`** | LOCAL | — | signs LP path | not a separate balance |
| **CDP / openclaw wallets** | EMPTY | — | **0 wallets** | `cdp-wallets.json` = `[]`; manager persists 0 |
| **Stripe** | BROKEN key | offchain | 0 | invalid `sk_live_…` in env |
| **Notion (ntn / diamondvault worker)** | DEGRADED | offchain | n/a | invalid/empty token; contracts `0x0` on Base & Polygon in worker config |
| **qflop-backfill orchestrator** | LIVE sim-ish | Base | uses HD set | registry `sim: true` in here.now copy; shm revenue **not cash** |
| **10pct-autonomy / polygon agents** | AGENT PROCS | — | no separate treasury | monitor/directive stack; does not mint spendable ETH |
| **diamondvault-notion-worker** | HEALTHY :8081 | config | — | `polygon_contract=0x0`, `base_contract=0x0` |

---

## Multichain balance check (controlled addresses)

| Address | Base ETH | Polygon | Optimism | Arbitrum |
|---------|----------|---------|----------|----------|
| `0x60C4…77d9` (LP) | **0.001197** | 0 | 0 | 0 |
| `0xe450…e330` (hd0) | 0.000035 | 0 | 0 | 0 |
| `0x8b53…A920` (hd1) | 0.000035 | 0 | 0 | 0 |
| hd2–hd24 | 0 | (not re-checked; Base zero earlier) | — | — |

---

## Notion double-check status

| Path | Result |
|------|--------|
| `ntn api v1/search` | **API token is invalid** |
| `qflop-backfill/.env` `NOTION_API_TOKEN` | placeholder `your-notion-…` |
| `load-env` / `~/.env` `NOTION_TOKEN` | unexpanded `${NOTION…}` |
| credential-vault | no usable Notion secret |
| Worker `config.json` | null contracts on Polygon & Base |
| Page id present | `BACKFILL_NOTION_PAGE_ID=4bea432f-…` (cannot read without token) |

**Action for operator:** run `ntn login` or set a real `NOTION_API_TOKEN` integration secret, then re-query pages *wQFLOP Liquidity — Plans & Projections* and any treasury DB.

---

## What *is* active (ops)

- `gas-keeper` (pm2) — keep LP ETH ≥ 0.0005; target 0.01 waits for external deposit  
- `lp-autoscale` (pm2) — live key loaded  
- `qflop-backfill` + recovery dashboard  
- Aerodrome Base pool only  

To fund **≥ 0.01 ETH** gas buffer: external transfer to `0x60C4499870f115664d7FfD8411b023DBEf3377d9` on **Base**. No polygon/hardhat/aerodrome side-treasury can currently fill that under keys we control.
