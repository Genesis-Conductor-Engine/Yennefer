# x402-cycle-intelligence

Publication surface for Genesis Conductor Yennefer Thermodynamic Daemon.

- `envelope_version`: `0.3.0`
- Advertises `thermodynamic_report` on candidate / report / intelligence
- Verification recomputes the report before `payload_digest`
- `simulated_projection` is advisory until live quotes + policy gates exist
- Checkout-sessions remain **deny** unless `eta_thermo >= 0.7` and `confidence >= 0.5` with live quotes

## Endpoints

| Method | Path | Returns |
| --- | --- | --- |
| GET | `/health` | service health |
| GET | `/.well-known/x402` | discovery advertising `thermodynamic_report` |
| POST | `/candidate` `/report` `/intelligence` | `thermodynamic_report` + digest |

Shopify SKU `GENESIS-YENNEFER-THERMO-REPORT` stays DRAFT until operator approval.
