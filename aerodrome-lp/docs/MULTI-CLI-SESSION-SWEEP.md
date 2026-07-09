# Multi-CLI session sweep (Codex · OpenCode · AGY · Gemini)

**Date:** 2026-07-09  
**Purpose:** Catch wallets / funding claims missed by Grok-only context.

---

## Session stores scanned

| CLI | Location | Volume / format | Wallet-relevant hits |
|-----|----------|-----------------|----------------------|
| **Codex** | `~/.codex/sessions/**/*.jsonl`, `history.jsonl`, `memories/rollout_summaries/` | 77 rollouts; 63 keyword matches | Partial-funding design; **2/25 real ETH historically (~0.00977 total)**; sim ledger $1.7M |
| **OpenCode** | `~/.local/share/opencode/opencode.db`, `prompt-history.jsonl` | SQLite + history | `cast wallet import qflop-lp`; vibe upgrades; **no new funded addresses** |
| **AGY** (`agy` = Antigravity CLI) | `~/.gemini/antigravity-cli/conversations/*.db` (56), `brain/**` | SQLite + artifacts | **`wallet_directory.md`**, LP reports, 51-session status — same EOAs as HD/LP set |
| **Gemini** | `~/.gemini/history`, settings, projects | Project roots only | Points at same diamondnode workspace; MCP list includes gc-mcp |

---

## AGY artifact: wallet directory (2026-06-16)

Source:  
`~/.gemini/antigravity-cli/brain/2f18cf10-…/wallet_directory.md`

| Role | Address | Then (AGY) | Now (live Base, 2026-07-09) |
|------|---------|------------|-----------------------------|
| LP Owner | `0x60C4499870f115664d7FfD8411b023DBEf3377d9` | 0.001039 ETH | **~0.00120 ETH** |
| Token Owner / Minter | `0x9545b6c5cfa22E3A1e4C31C4685e18770e513568` | 0 ETH | **0 ETH** |
| Workers 0–24 | HD `m/44'/60'/0'/0/{i}` | “Needs funding” | 0–1 dust only; 2–24 empty |
| Pool fees contract | `0x020f4868De01921B2c47f08eE3677AE9F56aF7B0` | listed | **0 ETH** (contract, not agent EOA) |

AGY also recorded **$1.9M “revenue” / 113% recovery** via `cashflow-stayalive-pump` — same synthetic path Codex/Grok already flagged (`sim: true` ledger).

---

## Codex findings (high signal)

| Session / summary | Finding |
|-------------------|---------|
| `…JeNM-qflop_backfill_mnemonic_ssh_partial_funding` | Canonical mnemonic in `qflop-backfill/.env`; real provision → **0/25 funded** at first; partial-funding mode designed for seed wallets |
| Rollout 2026-06-27 | **Funded (real ETH): 2 of 25** (max 0.005, total **0.00977 ETH**); profit ledger all `sim: true` / stayalive_pump; milestone 100% is **ledger math**, not chain |
| `…akng-financial_infrastructure_liquidity_control_plane…` | Control plane reads `/dev/shm/accumulated_liquidity.json` — not onchain treasury |
| Hardhat+Notion strategy thread | “tiny amounts funded in just several wallets” bootstrap — **strategy**, not a $15–20k pool |

---

## OpenCode findings

- Prompt history: `cast wallet import qflop-lp`, tunnel-through GitHub handoffs, vibe agent upgrades.
- DB messages: Cloudflare Workers / gc-mcp deploys — **no alternate agent treasury addresses**.

---

## Cross-check vs live agentic inventory

| Source claims | Live ground truth |
|---------------|-------------------|
| AGY “workers need funding” | Still true for 23/25 HD agents |
| Codex “2 of 25 funded (~0.01 ETH)” | Consistent order-of-magnitude with today (~0.001+ dust after LP gas harvest) |
| AGY/Codex “$1.7M–$1.9M recovered” | **Synthetic** shm meters, not spendable ETH |
| New addresses from AGY (token owner, fee collector) | **No ETH** to pull for gas |

---

## Conclusion

Codex, OpenCode, AGY, and Gemini sessions **agree** with the live inventory:

1. Agentic EOAs = **LP_OWNER + 25 HD workers** (builder codes).  
2. **No hidden $15–20k** treasury surfaces in those CLIs.  
3. Historical “funded agents” peaks were **~0.01 ETH total across 2 workers**, not thousands of USD.  
4. Large USD figures in AGY/Codex are the **stayalive/sim ledger**, not bankable funds.

See also: [AGENTIC-WALLETS.md](./AGENTIC-WALLETS.md), [INSTRUMENT-INVENTORY.md](./INSTRUMENT-INVENTORY.md).
