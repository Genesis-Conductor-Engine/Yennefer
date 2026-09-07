#!/usr/bin/env bash
# consolidate.sh — Sweep wQFLOP + WETH from all 25 backfill worker wallets to LP_OWNER.
# Also wraps any raw ETH > gas reserve into WETH on the LP_OWNER wallet.
#
# Modes:
#   --check     Read-only: show balances across fleet (DEFAULT)
#   --dry-run   Show what transfers would happen, don't broadcast
#   --live      Execute transfers (requires PRIVATE_KEY or mnemonic access)
#
# Usage:
#   bash consolidate.sh --check
#   bash consolidate.sh --dry-run
#   MNEMONIC="..." bash consolidate.sh --live
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REGISTRY="${HERE}/../qflop-backfill/config/wallet_registry.json"
LP_CFG="${HERE}/config/caps.json"

for b in cast jq python3; do command -v "$b" >/dev/null || { echo "missing: $b" >&2; exit 1; }; done

# Foundry `cast call … (uint256)` prints `INTEGER [SCI]`. Never int() or $((…)) the raw line.
PARSE_CAST_UINT="${HERE}/scripts/parse_cast_uint.py"
parse_cast_uint() { python3 "$PARSE_CAST_UINT" "${1-}"; }
uint_add() { python3 "$PARSE_CAST_UINT" --add "${1-}" "${2-}"; }
uint_gt() { python3 "$PARSE_CAST_UINT" --gt "${1-}" "${2-}"; }
fmt_eth() { python3 "$PARSE_CAST_UINT" --fmt-eth "${1-}"; }

# Load config
RPC=$(jq -r '.rpc_url' "$LP_CFG")
WQFLOP=$(jq -r '.addresses.wqflop' "$LP_CFG")
WETH=$(jq -r '.addresses.weth' "$LP_CFG")
QFLOP=$(jq -r '.addresses.qflop' "$LP_CFG")
LP_OWNER="${LP_OWNER:-$(grep LP_OWNER "${HERE}/.env" 2>/dev/null | sed 's/.*=//' | tr -d ' ')}"
[ -z "$LP_OWNER" ] && { echo "LP_OWNER not set — export it or add to .env" >&2; exit 1; }

MODE=check
GAS_RESERVE_WEI=500000000000000  # 0.0005 ETH kept per wallet for future gas
MIN_TRANSFER_WEI=1000000000000   # don't bother transferring dust < 0.000001

while [ $# -gt 0 ]; do case "$1" in
  --check) MODE=check;; --dry-run) MODE=dry-run;; --live) MODE=live;;
  -h|--help) grep '^#' "$0" | sed 's/^#\{1,\} \{0,1\}//'; exit 0;;
  *) echo "unknown: $1" >&2; exit 2;; esac; shift; done

# Read wallet addresses from registry
WALLETS=$(python3 -c "
import json
with open('$REGISTRY') as f:
    reg = json.load(f)
    ws = reg if isinstance(reg, list) else reg.get('wallets', [])
    for w in ws:
        print(w['address'])
")

echo "=============================================="
echo "  wQFLOP Fleet Consolidation → LP Owner"
echo "=============================================="
echo "  LP Owner:  $LP_OWNER"
echo "  Mode:      $MODE"
echo "  wQFLOP:    $WQFLOP"
echo "  WETH:      $WETH"
echo "  QFLOP:     $QFLOP"
echo "  Fleet:     $(echo "$WALLETS" | wc -l) wallets"
echo "=============================================="
echo ""

TOTAL_WQFLOP=0
TOTAL_QFLOP=0
TOTAL_ETH=0
TOTAL_WETH=0
TRANSFER_COUNT=0
DELAY=2  # seconds between RPC calls to avoid rate limiting

echo "== SCANNING FLEET BALANCES =="
for addr in $WALLETS; do
  sleep "$DELAY"
  
  # Get balances (with rate limit protection)
  W_WQFLOP=$(parse_cast_uint "$(cast call "$WQFLOP" "balanceOf(address)(uint256)" "$addr" --rpc-url "$RPC" 2>/dev/null || echo "0")")
  sleep 1
  W_QFLOP=$(parse_cast_uint "$(cast call "$QFLOP" "balanceOf(address)(uint256)" "$addr" --rpc-url "$RPC" 2>/dev/null || echo "0")")
  sleep 1
  W_ETH=$(parse_cast_uint "$(cast balance "$addr" --rpc-url "$RPC" 2>/dev/null | awk '{print $1}' || echo "0")")
  sleep 1
  W_WETH=$(parse_cast_uint "$(cast call "$WETH" "balanceOf(address)(uint256)" "$addr" --rpc-url "$RPC" 2>/dev/null || echo "0")")
  
  # Only print wallets with non-zero balances
  HAS_BALANCE=0
  [ "$W_WQFLOP" != "0" ] && HAS_BALANCE=1
  [ "$W_QFLOP" != "0" ] && HAS_BALANCE=1
  [ "$(uint_gt "$W_ETH" "$MIN_TRANSFER_WEI")" = "1" ] && HAS_BALANCE=1
  [ "$W_WETH" != "0" ] && HAS_BALANCE=1
  
  if [ "$HAS_BALANCE" = "1" ]; then
    ETH_FMT=$(fmt_eth "$W_ETH" 2>/dev/null || echo "?")
    echo "  ${addr}:"
    echo "    ETH: $ETH_FMT | wQFLOP: $W_WQFLOP | QFLOP: $W_QFLOP | WETH: $W_WETH"
    
    TOTAL_WQFLOP=$(uint_add "$TOTAL_WQFLOP" "$W_WQFLOP")
    TOTAL_QFLOP=$(uint_add "$TOTAL_QFLOP" "$W_QFLOP")
    TOTAL_ETH=$(uint_add "$TOTAL_ETH" "$W_ETH")
    TOTAL_WETH=$(uint_add "$TOTAL_WETH" "$W_WETH")
    TRANSFER_COUNT=$((TRANSFER_COUNT + 1))
  fi
done

echo ""
echo "== FLEET TOTALS =="
echo "  wQFLOP: $TOTAL_WQFLOP"
echo "  QFLOP:  $TOTAL_QFLOP"
echo "  ETH:    $(fmt_eth "$TOTAL_ETH")"
echo "  WETH:   $TOTAL_WETH"
echo "  Wallets with balance: $TRANSFER_COUNT"

echo ""
echo "== LP OWNER BALANCES =="
sleep "$DELAY"
LP_ETH=$(parse_cast_uint "$(cast balance "$LP_OWNER" --rpc-url "$RPC" 2>/dev/null | awk '{print $1}' || echo "0")")
sleep 1
LP_WQFLOP=$(parse_cast_uint "$(cast call "$WQFLOP" "balanceOf(address)(uint256)" "$LP_OWNER" --rpc-url "$RPC" 2>/dev/null || echo "0")")
sleep 1
LP_WETH=$(parse_cast_uint "$(cast call "$WETH" "balanceOf(address)(uint256)" "$LP_OWNER" --rpc-url "$RPC" 2>/dev/null || echo "0")")
sleep 1
LP_QFLOP=$(parse_cast_uint "$(cast call "$QFLOP" "balanceOf(address)(uint256)" "$LP_OWNER" --rpc-url "$RPC" 2>/dev/null || echo "0")")
echo "  ETH:    $(fmt_eth "$LP_ETH")"
echo "  WETH:   $LP_WETH"
echo "  wQFLOP: $LP_WQFLOP"
echo "  QFLOP:  $LP_QFLOP"

if [ "$MODE" = "check" ]; then
  echo ""
  echo "== RECOMMENDED ACTIONS =="
  [ "$(uint_gt "$TOTAL_WQFLOP" "0")" = "1" ] && echo "  → Sweep $TOTAL_WQFLOP wQFLOP to LP Owner"
  [ "$(uint_gt "$TOTAL_QFLOP" "0")" = "1" ] && echo "  → Wrap $TOTAL_QFLOP QFLOP → wQFLOP, then sweep"
  [ "$(uint_gt "$TOTAL_WETH" "0")" = "1" ] && echo "  → Sweep $TOTAL_WETH WETH to LP Owner"
  echo "  → Fund LP Owner with gas ETH (needs ~0.01 ETH minimum)"
  echo ""
  echo "Run with --dry-run to see transfer plan, or --live to execute."
  exit 0
fi

if [ "$MODE" = "dry-run" ]; then
  echo ""
  echo "== TRANSFER PLAN (DRY-RUN) =="
  echo "  Would transfer all wQFLOP, QFLOP, and WETH from fleet to $LP_OWNER"
  echo "  Would keep $GAS_RESERVE_WEI wei ETH per wallet as gas reserve"
  echo "  No transactions broadcast."
  exit 0
fi

if [ "$MODE" = "live" ]; then
  echo ""
  echo "== LIVE EXECUTION =="
  echo "  ⚠️  Live mode requires the HD wallet mnemonic to derive worker private keys."
  echo "  Set MNEMONIC env var or provide individual PRIVATE_KEY per wallet."
  echo ""
  
  MNEMONIC="${MNEMONIC:-}"
  if [ -z "$MNEMONIC" ]; then
    echo "REFUSED: MNEMONIC not set. Export it before running --live."
    echo "  Example: MNEMONIC=\"word1 word2 ...\" bash consolidate.sh --live"
    exit 3
  fi
  
  for i in $(seq 0 $(($(echo "$WALLETS" | wc -l) - 1))); do
    addr=$(echo "$WALLETS" | sed -n "$((i+1))p")
    # Derive worker private key from mnemonic path m/44'/60'/0'/0/i (ethers HD)
    WORKER_KEY=$(
      IDX="$i" MNEMONIC="$MNEMONIC" NODE_PATH="${HERE}/../qflop-backfill/node_modules:${HERE}/node_modules" \
      node --input-type=module <<'NODE' 2>/dev/null || true
import { ethers } from "ethers";
const path = `m/44'/60'/0'/0/${process.env.IDX}`;
const w = ethers.HDNodeWallet.fromMnemonic(ethers.Mnemonic.fromPhrase(process.env.MNEMONIC), path);
process.stdout.write(w.privateKey);
NODE
    )
    [ -z "$WORKER_KEY" ] && { echo "  SKIP $addr: could not derive key for index $i"; continue; }
    
    # Transfer wQFLOP
    W_WQFLOP=$(parse_cast_uint "$(cast call "$WQFLOP" "balanceOf(address)(uint256)" "$addr" --rpc-url "$RPC" 2>/dev/null || echo "0")")
    if [ "$W_WQFLOP" != "0" ]; then
      echo "  [$i] $addr → transfer $W_WQFLOP wQFLOP to LP Owner"
      cast send "$WQFLOP" "transfer(address,uint256)" "$LP_OWNER" "$W_WQFLOP" \
        --private-key "$WORKER_KEY" --rpc-url "$RPC" 2>&1 | tail -3
      sleep 2
    fi
    
    # Transfer WETH
    W_WETH=$(parse_cast_uint "$(cast call "$WETH" "balanceOf(address)(uint256)" "$addr" --rpc-url "$RPC" 2>/dev/null || echo "0")")
    if [ "$W_WETH" != "0" ]; then
      echo "  [$i] $addr → transfer $W_WETH WETH to LP Owner"
      cast send "$WETH" "transfer(address,uint256)" "$LP_OWNER" "$W_WETH" \
        --private-key "$WORKER_KEY" --rpc-url "$RPC" 2>&1 | tail -3
      sleep 2
    fi
    
    # Wrap QFLOP → wQFLOP and transfer
    W_QFLOP=$(parse_cast_uint "$(cast call "$QFLOP" "balanceOf(address)(uint256)" "$addr" --rpc-url "$RPC" 2>/dev/null || echo "0")")
    if [ "$W_QFLOP" != "0" ]; then
      echo "  [$i] $addr → approve + wrap $W_QFLOP QFLOP → wQFLOP"
      cast send "$QFLOP" "approve(address,uint256)" "$WQFLOP" "$W_QFLOP" \
        --private-key "$WORKER_KEY" --rpc-url "$RPC" 2>&1 | tail -2
      sleep 1
      cast send "$WQFLOP" "depositFor(address,uint256)" "$LP_OWNER" "$W_QFLOP" \
        --private-key "$WORKER_KEY" --rpc-url "$RPC" 2>&1 | tail -3
      sleep 2
    fi
  done
  echo ""
  echo "== CONSOLIDATION COMPLETE =="
  echo "Re-run with --check to verify final balances."
fi
