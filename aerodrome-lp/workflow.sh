#!/usr/bin/env bash
# Dynamic liquidity workflow for wQFLOP/WETH on Aerodrome (Base).
#
# Loop: ASSESS (live reads) -> DECIDE (HOLD by default if pool degenerate / caps hit)
#       -> SIMULATE (forge fork-sim) -> EXECUTE (live, only if --live + .ARMED + within caps)
#       -> RECORD (projection.json + projection.md for the subagent to push to Notion).
#
# Modes:
#   --status            read-only assessment + projection (no sim, no tx)
#   --dry-run           assess + decide + fork-simulate the add (DEFAULT; never broadcasts)
#   --live              as dry-run, then broadcast IF .ARMED present and decision==ADD
# Flags:
#   --max-weth <eth>    override per-tx WETH cap downward (e.g. 0.002 for first live)
#   --force-seed        allow adding into a DEGENERATE pool (you accept setting the price)
#
# Signing (live only, never logged): set SIGNER_ACCOUNT (foundry keystore alias, preferred)
#   or PRIVATE_KEY in the environment. LP_OWNER must be the signer's address.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CFG="$HERE/config/caps.json"; STATE="$HERE/config/state.json"
ARMED="$HERE/.ARMED"; PROJ_JSON="$HERE/projections.json"; PROJ_MD="$HERE/projection.md"

for b in jq cast forge python3 date; do command -v "$b" >/dev/null || { echo "missing dependency: $b" >&2; exit 1; }; done
cfg(){ jq -r "$1" "$CFG"; }
RPC=$(cfg .rpc_url); WETH=$(cfg .addresses.weth); WQFLOP=$(cfg .addresses.wqflop)
POOL=$(cfg .addresses.pool_wqflop_weth); VOTER=$(cfg .addresses.voter)
MIN_WETH_RES=$(cfg .caps.min_weth_reserve_for_add_wei)
MAX_TX_ETH=$(cfg .caps.max_weth_per_tx_eth); DAILY_ETH=$(cfg .caps.daily_weth_cap_eth)
SLIP=$(cfg .caps.max_slippage_bps)

MODE=dry-run; FORCE=0; MAXW=""
while [ $# -gt 0 ]; do case "$1" in
  --status) MODE=status;; --dry-run) MODE=dry-run;; --live) MODE=live;;
  --force-seed) FORCE=1;; --max-weth) MAXW="${2:-}"; shift;;
  -h|--help) grep '^#' "$0" | sed 's/^#\{1,\} \{0,1\}//'; exit 0;;
  *) echo "unknown arg: $1" >&2; exit 2;; esac; shift; done

RPCJ(){ cast call "$@" --rpc-url "$RPC" --json | jq -r '.[0]'; }
w(){ cast to-wei "$1" ether; }
MAX_TX_WEI=$(w "$MAX_TX_ETH"); DAILY_WEI=$(w "$DAILY_ETH")
[ -n "$MAXW" ] && MAX_TX_WEI=$(w "$MAXW")
OWNER="${LP_OWNER:-}"

echo "== ASSESS =="
RES=$(cast call "$POOL" "getReserves()(uint256,uint256,uint256)" --rpc-url "$RPC" --json)
R0=$(jq -r '.[0]' <<<"$RES"); R1=$(jq -r '.[1]' <<<"$RES")
T0=$(RPCJ "$POOL" "token0()(address)")
if [ "${T0,,}" = "${WETH,,}" ]; then WETH_RES=$R0; WQ_RES=$R1; else WETH_RES=$R1; WQ_RES=$R0; fi
GAUGE=$(RPCJ "$VOTER" "gauges(address)(address)" "$POOL")
echo "  pool=$POOL  WETH_res=$WETH_RES  wQFLOP_res=$WQ_RES  gauge=$GAUGE"

OWNER_WETH=0; OWNER_WQ=0; OWNER_ETH=0; OWNER_LP=0
if [ -n "$OWNER" ]; then
  OWNER_WETH=$(RPCJ "$WETH"   "balanceOf(address)(uint256)" "$OWNER")
  OWNER_WQ=$(  RPCJ "$WQFLOP" "balanceOf(address)(uint256)" "$OWNER")
  OWNER_LP=$(  RPCJ "$POOL"   "balanceOf(address)(uint256)" "$OWNER")
  OWNER_ETH=$( cast balance "$OWNER" --rpc-url "$RPC" | awk '{print $1}')
  echo "  owner=$OWNER  ETH=$OWNER_ETH  WETH=$OWNER_WETH  wQFLOP=$OWNER_WQ  LP=$OWNER_LP"
fi

TODAY=$(date -u +%F); SPENT=0
if [ -f "$STATE" ]; then
  [ "$(jq -r '.date // ""' "$STATE")" = "$TODAY" ] && SPENT=$(jq -r '.weth_spent_wei // "0"' "$STATE")
fi

echo "== DECIDE =="
read -r DECISION REASON ADD_WETH ADD_WQ < <(python3 - "$WETH_RES" "$WQ_RES" "$MIN_WETH_RES" "$MAX_TX_WEI" "$DAILY_WEI" "$SPENT" "$OWNER_WETH" "$OWNER_WQ" "$FORCE" <<'PY'
import sys
wr,wq,minr,maxtx,daily,spent,ow,oq,force = (int(x or 0) for x in sys.argv[1:10])
def out(d,r,aw=0,aq=0): print(d,r,aw,aq); raise SystemExit
if daily-spent <= 0: out("HOLD","daily_cap_reached")
if wr < minr and not force: out("HOLD","pool_degenerate_weth_dust")
if wr == 0: out("HOLD","zero_weth_reserve")
addw = min(maxtx, daily-spent, ow)
if addw <= 0: out("HOLD","no_weth_available")
addq = addw * wq // wr
if addq <= 0: out("HOLD","computed_wqflop_zero")
if addq > oq:
    addq = oq
    addw = addq * wr // wq
    if addw <= 0: out("HOLD","insufficient_wqflop")
out("ADD","within_caps",addw,addq)
PY
)
echo "  decision=$DECISION reason=$REASON add_WETH=$ADD_WETH add_wQFLOP=$ADD_WQ (daily spent=$SPENT / cap=$DAILY_WEI)"

SIM_OUT=""; TX_OUT=""
run_forge(){ # $1=extra args
  WETH_AMOUNT="$ADD_WETH" WQFLOP_AMOUNT="$ADD_WQ" MAX_WETH_PER_TX="$MAX_TX_WEI" SLIPPAGE_BPS="$SLIP" LP_OWNER="$OWNER" \
    forge script script/AddLiquidity.s.sol --rpc-url "$RPC" --sender "$OWNER" $1 2>&1
}

if [ "$DECISION" = "ADD" ] && [ "$MODE" != "status" ]; then
  [ -z "$OWNER" ] && { echo "LP_OWNER required to simulate/execute an ADD" >&2; exit 3; }
  echo "== SIMULATE (fork) =="; SIM_OUT="$(run_forge "")"; echo "$SIM_OUT" | tail -12
  if [ "$MODE" = "live" ]; then
    [ -f "$ARMED" ] || { echo "REFUSED: .ARMED flag absent — live execution disabled. (touch $ARMED to arm)"; MODE=dry-run; }
  fi
  if [ "$MODE" = "live" ] && echo "$SIM_OUT" | grep -q "LP minted"; then
    SIGNER=(); if [ -n "${SIGNER_ACCOUNT:-}" ]; then SIGNER=(--account "$SIGNER_ACCOUNT" --sender "$OWNER");
      elif [ -n "${PRIVATE_KEY:-}" ]; then SIGNER=(--private-key "$PRIVATE_KEY");
      else echo "REFUSED: no signer (SIGNER_ACCOUNT or PRIVATE_KEY)"; exit 4; fi
    echo "== EXECUTE (broadcast) =="
    TX_OUT="$(WETH_AMOUNT="$ADD_WETH" WQFLOP_AMOUNT="$ADD_WQ" MAX_WETH_PER_TX="$MAX_TX_WEI" SLIPPAGE_BPS="$SLIP" LP_OWNER="$OWNER" \
      forge script script/AddLiquidity.s.sol --rpc-url "$RPC" --broadcast "${SIGNER[@]}" 2>&1)"; echo "$TX_OUT" | tail -15
    if echo "$TX_OUT" | grep -qiE "ONCHAIN EXECUTION COMPLETE|Transactions saved"; then
      NEWSPENT=$(python3 -c "print($SPENT+$ADD_WETH)")
      printf '{"date":"%s","weth_spent_wei":"%s"}\n' "$TODAY" "$NEWSPENT" > "$STATE"
      echo "  daily state updated: spent=$NEWSPENT / cap=$DAILY_WEI"
    fi
  fi
fi

echo "== RECORD =="
PRICE=$(python3 -c "print(($WETH_RES*10**18)//$WQ_RES if $WQ_RES else 0)")
DEGEN=$([ "$WETH_RES" -lt "$MIN_WETH_RES" ] && echo true || echo false)
python3 - "$PROJ_JSON" "$TODAY" "$POOL" "$WETH_RES" "$WQ_RES" "$PRICE" "$GAUGE" "$DECISION" "$REASON" "$ADD_WETH" "$ADD_WQ" "$OWNER_LP" "$DEGEN" "$SPENT" "$DAILY_WEI" <<'PY'
import json,sys
p,today,pool,wr,wq,price,gauge,dec,reason,aw,aq,lp,degen,spent,daily = sys.argv[1:16]
json.dump({"date":today,"pool":pool,"weth_reserve_wei":wr,"wqflop_reserve_wei":wq,
  "price_wei_per_1e18_wqflop":price,"gauge":gauge,"pool_degenerate":degen=="true",
  "decision":dec,"reason":reason,"add_weth_wei":aw,"add_wqflop_wei":aq,
  "owner_lp_balance":lp,"daily_weth_spent_wei":spent,"daily_weth_cap_wei":daily},
  open(p,"w"),indent=2)
PY
{
  echo "# wQFLOP/WETH Liquidity — Plans & Projections ($TODAY)"
  echo ""
  echo "- Pool: \`$POOL\` (Aerodrome volatile)"
  echo "- Reserves: WETH=$WETH_RES wei, wQFLOP=$WQ_RES wei"
  echo "- Price: ~$PRICE wei per 1e18 wQFLOP  | Degenerate: $DEGEN | Gauge: $GAUGE"
  echo "- Decision: **$DECISION** ($REASON); proposed add WETH=$ADD_WETH wQFLOP=$ADD_WQ"
  echo "- Daily cap usage: $SPENT / $DAILY_WEI wei"
  echo ""
  echo "_Subagent: push this to Notion via the notion-cli skill (page: 'wQFLOP Liquidity — Plans & Projections')._"
} > "$PROJ_MD"
echo "  wrote $PROJ_JSON and $PROJ_MD"
echo "DONE ($MODE)"
