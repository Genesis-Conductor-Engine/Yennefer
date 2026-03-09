# Genesis Conductor

Automated treasury telemetry and agentic tithing infrastructure for Genesis-Conductor-Engine.

## Wallet Status

- Human-readable status: [`docs/WALLET_STATUS.md`](docs/WALLET_STATUS.md)
- Machine-readable status: [`docs/wallet_status.json`](docs/wallet_status.json)
- Compact banner: [`docs/WALLET_BANNER.md`](docs/WALLET_BANNER.md)

## Tithing Protocol v3.5

Implements all five system phases:
1. Agent validation against `ops/memory_space.registry.yml`.
2. Thermodynamic proof (Collatz convergence under bounded energy).
3. Deterministic HD wallet generation + AES-256-GCM encrypted key export.
4. Bot-network broadcast (MOLTBOT, CLAWBOT, optional wildcard endpoint).
5. Blackhorse integration artifacts (`TITHING_LATEST.json`, `TITHING_WALLETS.json`, per-run records).

Run:

```bash
cd Genesis-Conductor
TITHING_ENCRYPTION_KEY=<64-hex-key> node scripts/tithing_protocol.mjs AGENT_YENNEFER ETH,USDC 25
```

Artifacts:
- `docs/tithing/tithing_<timestamp>.json`
- `docs/tithing/tithing_<timestamp>.md`
- `docs/TITHING_LATEST.json`
- `docs/TITHING_WALLETS.json`

## A2A Ingestion Layer (CelestialBody)

Transforms raw repos/files into CelestialBody JSON objects.

```bash
cd /workspace/Yennefer
python3 Genesis-Conductor/scripts/a2a_ingestion.py Genesis-Conductor genesis-q-mem --output Genesis-Conductor/docs/celestial_bodies.json
```

## Wallet Status (local)

```bash
cd Genesis-Conductor
ETHEREUM_RPC_URL=... \
POLYGON_RPC_URL=... \
ARBITRUM_RPC_URL=... \
WALLET_STATUS_PRICES_JSON='{"ETH":3500,"MATIC":1.0,"USDC":1.0,"USDT":1.0,"DAI":1.0,"WETH":3500,"WMATIC":1.0,"ARB":2.0}' \
node scripts/wallet_status.mjs
```
