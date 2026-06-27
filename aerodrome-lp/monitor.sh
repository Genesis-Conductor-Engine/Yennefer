#!/usr/bin/env bash
# Pool health monitor — cron-safe, no signing.
# Emits JSON: status HEALTHY|DEGENERATE|NEAR_THRESHOLD + optional GAUGE_MISSING
# Exit 0 = healthy; 1 = action needed
# Cron: */5 * * * * bash ~/Yennefer/aerodrome-lp/monitor.sh >> ~/Yennefer/aerodrome-lp/logs/monitor.log 2>&1
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CFG="$HERE/config/caps.json"
mkdir -p "$HERE/logs"

RPC="https://mainnet.base.org"
POOL=$(jq -r .addresses.pool_wqflop_weth "$CFG")
VOTER=$(jq -r .addresses.voter "$CFG")
WETH_ADDR=$(jq -r .addresses.weth "$CFG")
MIN_WETH=$(jq -r .caps.min_weth_reserve_for_add_wei "$CFG")
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Parse reserves: cast returns one value per line
mapfile -t RESS < <(cast call "$POOL" "getReserves()(uint256,uint256,uint256)" --rpc-url "$RPC" | awk '{print $1}')
R0="${RESS[0]}"; R1="${RESS[1]}"
T0=$(cast call "$POOL" "token0()(address)" --rpc-url "$RPC" | awk '{print $1}')

if [ "${T0,,}" = "${WETH_ADDR,,}" ]; then WETH_RES="$R0"; else WETH_RES="$R1"; fi
GAUGE=$(cast call "$VOTER" "gauges(address)(address)" "$POOL" --rpc-url "$RPC" | awk '{print $1}')

python3 - "$TS" "$WETH_RES" "$MIN_WETH" "$GAUGE" "$POOL" <<'PY'
import json, sys
ts, wr_s, minr_s, gauge, pool = sys.argv[1:]
wr = int(wr_s); minr = int(minr_s)

status = "HEALTHY" if wr >= minr else "DEGENERATE"
near = int(minr * 1.2)
if wr >= minr and wr < near: status = "NEAR_THRESHOLD"
gauge_ok = gauge.lower() != "0x"+"0"*40
if not gauge_ok: status += "+GAUGE_MISSING"

needed = max(0, minr - wr)
entry = {
    "ts": ts, "status": status,
    "weth_reserve_wei": wr, "weth_reserve_eth": round(wr/1e18, 8),
    "min_threshold_wei": minr, "min_threshold_eth": round(minr/1e18, 6),
    "weth_needed_wei": needed, "weth_needed_eth": round(needed/1e18, 8),
    "weth_needed_usd": round(needed/1e18 * 3500, 4),
    "gauge_ok": gauge_ok, "gauge_addr": gauge, "pool": pool,
}
print(json.dumps(entry))
import sys; sys.exit(0 if wr >= minr and gauge_ok else 1)
PY
