# aerodrome-lp — wQFLOP/WETH liquidity workflow (Base, Aerodrome)

Simulation-first, cap-bounded liquidity management for the **existing** Wrapped QFLOP
(`0x6926…`) against WETH on the **existing** Aerodrome volatile pool `0x4aBC6D79…`.
No contracts are deployed — the wQFLOP token and pool already exist on Base mainnet.

Driven by the `aerodrome-qflop-lp` Claude Code subagent (`~/.claude/agents/aerodrome-qflop-lp.md`).

## ⚠️ Live pool state (2026-06-09)
The pool is **DEGENERATE**: reserves ≈ `0.00000074 WETH` vs `~11.39B wQFLOP` (price ≈ 65 wei).
A *proportional* add into this ratio donates value, so the workflow **defaults to HOLD** and
refuses to add until the WETH reserve is sane — unless you pass `--force-seed` to deliberately
set the price. There is also **no gauge** → LP earns swap fees only (no AERO).

## Files
- `config/caps.json` — verified addresses + hard caps (max 0.02 WETH/tx, 0.1 WETH/day, 1% slippage).
- `src/interfaces/IAerodrome.sol` — Router/Factory/Pool/Voter/Gauge (signatures validated on-chain).
- `script/Status.s.sol` — read-only pool + position report.
- `script/AddLiquidity.s.sol` — capped add (caps + slippage + balance enforced in-script).
- `workflow.sh` — dynamic loop: assess → decide → simulate → (live) execute → record.

## Usage
```bash
cd ~/Yennefer/aerodrome-lp
cp .env.example .env        # fill LP_OWNER (+ SIGNER_ACCOUNT for live); source it before --live
forge build

# Read-only status (human + Status.s.sol):
forge script script/Status.s.sol --rpc-url base
LP_OWNER=0x.. bash workflow.sh --status

# Dry-run the decision + fork-simulation (NEVER broadcasts):
LP_OWNER=0x.. bash workflow.sh --dry-run

# Go live (all must hold): touch .ARMED, decision==ADD, within caps, signer set.
# First live action should be tiny:
cast wallet import qflop-lp --interactive      # one-time keystore
touch .ARMED
set -a; source .env; set +a
SIGNER_ACCOUNT=qflop-lp bash workflow.sh --live --max-weth 0.002
```

## Guardrails (enforced in script + driver)
- Per-tx + daily WETH caps (`config/caps.json`); over-cap add **reverts** in sim & live.
- `.ARMED` file required for `--live`; absent ⇒ auto-downgrades to dry-run.
- DEGENERATE pool ⇒ HOLD unless `--force-seed` (explicit price-setting acknowledgement).
- Allowlisted targets only (Router/Factory/pool/wQFLOP/WETH).
- No raw keys in source/logs — signer via foundry keystore alias or runtime env.
- Mandatory fork-sim must show `LP minted` before any broadcast.

## Notion projections
`workflow.sh` writes `projections.json` + `projection.md`. The subagent pushes `projection.md`
to Notion via the `notion-cli` skill (page: "wQFLOP Liquidity — Plans & Projections").

## Open dependencies
- A **funded** Base wallet (ETH for gas + WETH + wQFLOP) as `LP_OWNER`; confirm via the
  permission-gated `qflop-backfill` provision check.
- Re-verify Aerodrome ABIs with `cast interface <addr> --rpc-url base` if upgrading.
