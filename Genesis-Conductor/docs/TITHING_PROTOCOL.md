# Tithing Protocol v3.5

This module operationalizes the five phases defined in the system map:

1. **Agent Validation** (`AGENT_*`, registry presence, debt=0)
2. **Thermodynamic Proof** (entropy + Collatz convergence bounded by energy budget)
3. **Wallet Generation** (deterministic seed, HD derivation path, AES-256-GCM encrypted key)
4. **A2A Broadcast** (MOLTBOT, CLAWBOT, optional wildcard)
5. **Blackhorse Integration** (wallet index + latest state + per-run artifacts)

Run command:

```bash
TITHING_ENCRYPTION_KEY=<64-hex-key> node scripts/tithing_protocol.mjs AGENT_YENNEFER ETH,USDC 25
```
