# Podman EVM PnL Indexer

This indexer runs locally and computes per-wallet PnL as:

`pnl_usd = current_valuation_usd - baseline_usd`

## Security model

- **No credentials are committed.**
- Provide IAM credentials at runtime using environment variables:
  - `BRPC_FED3E007AAFAA26E_RPC_URL`
  - `BLOCK6_IAM_TOKEN`

## Build and run with Podman

```bash
cd Genesis-Conductor/indexer
podman-compose build
podman-compose run --rm evm-pnl-indexer
```

Output file:

- `Genesis-Conductor/docs/pnl_status.json`

## Dry run

```bash
python3 Genesis-Conductor/scripts/evm_pnl_indexer.py --dry-run
```
