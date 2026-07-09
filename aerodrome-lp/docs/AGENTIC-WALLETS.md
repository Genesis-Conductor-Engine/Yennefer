# Agentic wallet inventory (2026-07-09)

## Sets we actually have

| Set | Count | Kind | Spendable Base ETH | Notes |
|-----|------:|------|--------------------:|-------|
| **HD agent EOAs** (`BACKFILL_MASTER_MNEMONIC` `m/44'/60'/0'/0/{0..24}`) | 25 | Real EOAs | **~0.00007** (idx 0–1 dust only) | Same addresses as builder codes |
| **Builder Codes** (`base-build/artifacts/wallet_builder_codes.json`) | 25 | ERC-8021 attribution IDs on those EOAs | (same wallets) | `bc_*` per index |
| **LP / operator** | 1 | EOA = `PRIVATE_KEY` | **~0.00120** | `0x60C4499870f115664d7FfD8411b023DBEf3377d9` |
| **Registry file** (`qflop-backfill/config/wallet_registry.json`) | 25 | **SIM placeholders** | 0 | `sim: true`, addrs `0x1000…0000`–`0x1000…0018`, funded flags fake |
| **CDP / openclaw agent wallets** | 0 | — | 0 | `cdp-wallets.json` empty; manager recovery-loop failures historically |
| **Coinbase AgentKit smart wallet** | unprovisioned / empty data | CDP EVM provider | 0 | defaults `base-sepolia`; no funded mainnet export found |
| **payments-mcp agentic wallet** | installed, disabled | Electron Coinbase agentic | n/a | Grok `disabled_mcp_servers` includes payments-mcp; headless fail |

**Total liquid under agentic EOAs (Base):** ≈ **0.00127 ETH (~$2.21)** — almost all on LP_OWNER after gas bootstrap.

---

## Real agentic EOAs (Base balances)

| idx | address | ETH | builder code |
|----:|---------|-----:|--------------|
| 0 | `0xe4504e6FF6f2974e2b83b3fc193538DDab36e330` | 0.00003487 | bc_7dbm4r82 |
| 1 | `0x8b5346e88e1bD0B8Ad8F86d349f4985d7Df2A920` | 0.00003487 | bc_cpmpb10p |
| 2 | `0x5DdA6431a738aAF174d730F7F68145842a16c5e2` | 0 | bc_2fplty4b |
| 3 | `0x8B32Ce51DF2Bd2e427F762997230a734B0b70A1B` | 0 | bc_wekz7oen |
| 4 | `0x25781Ca3c03b17feF5dE7AEE268CFaC939B37D85` | 0 | bc_0x0wfoeg |
| 5 | `0xE6209Ce6e35c626C6f43E1d757B8f2F3B18E7c1a` | 0 | bc_cd23n05q |
| 6 | `0x9e096D19303Be4e9C13BBdec36C5c070f4D24b16` | 0 | bc_l2bxwrd3 |
| 7 | `0xF412d774261FB80f5ce16aF8962Ec53fD6c8b32c` | 0 | bc_wsm6khlh |
| 8 | `0x9Edb4BB47bd1167cb99A75b01dF3f3Fe76Fdb198` | 0 | bc_opbvoba1 |
| 9 | `0x17e17b4D6D3996dA8B270eebd650508dB9bf8A86` | 0 | bc_7k7mo30i |
| 10 | `0x0197F8ad4446871B60577849BF464E383eF3Fc15` | 0 | bc_9lxcfecv |
| 11 | `0xb5089526e1317cec7Eb5Cb6E974F878CE8bfe1fD` | 0 | bc_5u6jat69 |
| 12 | `0x66879b97C7d8A06e857Ecc6e5d6b21f7BF9373fD` | 0 | bc_7w0qjof5 |
| 13 | `0x10Ae089Bf27B9066daC3ed7985c430BC946e09a5` | 0 | bc_7dvi82zj |
| 14 | `0xD06A72a0C67C5D287F0621E2D844C8b6F7C7dc2e` | 0 | bc_99khojv0 |
| 15 | `0x7994D804D9a057cA8271879F030241e4F46BFDa2` | 0 | bc_zr0dsj5o |
| 16 | `0x2E74b32be6D5E42b3a362afe8E2C1fF8177b41eb` | 0 | bc_anpwoxje |
| 17 | `0xc80a456306879d81B5b97a13C1C43539A8650602` | 0 | bc_1s9pf3tw |
| 18 | `0xA81180170301eAF305e2c4957BE5BEE06C3A0E19` | 0 | bc_rl8cuats |
| 19 | `0x86b620D86cc2506e102a3a6b354a29cAd17bB170` | 0 | bc_4lslm55k |
| 20 | `0xC479696784c6cb631D45541aB29D50eFB79C8F52` | 0 | bc_ijb2sfbj |
| 21 | `0x28aFb1da519F5a43156b73247994e59b671011c5` | 0 | bc_ksgu5vuv |
| 22 | `0x3FE21a6Ff43Cb4B52822a766f960Cc64d7B5Fb1a` | 0 | bc_yiyp118o |
| 23 | `0x3723E12ee4e20a2D4Fd53Eb673F3EfE06cF5E686` | 0 | bc_kgxij0bc |
| 24 | `0xBfb0Bcf13B3B4EB984f450B8eD8B96be1B796E1C` | 0 | bc_pye3oq57 |
| OP | `0x60C4499870f115664d7FfD8411b023DBEf3377d9` | **0.00119740** | (operator / LP) |

Path: `m/44'/60'/0'/0/{index}` from `BACKFILL_MASTER_MNEMONIC`.  
Orchestrator (`qflop-backfill` pm2) spawns pipeline workers per index when not in pure sim.

---

## What looks like “25 funded agent wallets” but isn’t

`wallet_registry.json` reports `funded: true` × 25 with `sim: true` and fake addresses `0x1000…`.  
MCP `list_wallets` / recovery dashboard meters read that registry + `/dev/shm` ledgers — **not** live Base balances. That is the source of multi‑million “agent wallet” revenue illusions.

---

## Other agentic wallet stacks (status)

| Stack | Path / surface | Status |
|-------|----------------|--------|
| CDP wallet manager | pm2 `cdp-wallet-manager` | Online but **0 wallets** persisted; historical recovery alerts |
| OpenClaw CDP agent | `.openclaw/agents/cdp-wallet-agent.json` | Spec only (`list_wallets` tool) |
| AgentKit MCP | `cdp-agentkit-mcp` | Code present; network default **base-sepolia** |
| payments-mcp | Coinbase agentic + x402 | Installed; **disabled** in Grok; needs display for Electron |
| qflop base wallet MCP | `diamondnode-qflop-base-wallet-mcp` | Lists registry (sim unless re-provisioned real) |

---

## Implication for gas / 1 ETH goal

Agentic wallets **do not** form a $15k–$20k pool. Only LP_OWNER has operational ETH; HD agents 0–1 hold dust; 2–24 empty. Funding path remains external Base deposit to LP_OWNER (or batch-fund HD agents via `provision:partial` after real ETH arrives).
