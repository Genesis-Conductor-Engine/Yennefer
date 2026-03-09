#!/usr/bin/env python3
"""Lightweight EVM PnL indexer for Podman runtime."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from decimal import Decimal, getcontext
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

import requests
import yaml

getcontext().prec = 42

ERC20_BALANCE_OF = "0x70a08231"


@dataclass
class RpcClient:
    url: str
    headers: dict[str, str]
    timeout_seconds: int

    def call(self, method: str, params: list[Any]) -> Any:
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        response = requests.post(self.url, headers=self.headers, json=payload, timeout=self.timeout_seconds)
        response.raise_for_status()
        data = response.json()
        if data.get("error"):
            raise RuntimeError(f"RPC error for {method}: {data['error']}")
        return data["result"]


def load_config(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def is_address(value: str) -> bool:
    return isinstance(value, str) and value.startswith("0x") and len(value) == 42


def to_decimal(raw_hex: str, decimals: int) -> Decimal:
    return Decimal(int(raw_hex, 16)) / (Decimal(10) ** Decimal(decimals))


def encode_balance_of(wallet: str) -> str:
    wallet_hex = wallet.lower().replace("0x", "")
    return ERC20_BALANCE_OF + wallet_hex.rjust(64, "0")


def fetch_balances(client: RpcClient, network: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for wallet in network.get("wallets", []):
        address = wallet.get("address", "")
        if not is_address(address):
            rows.append({"wallet": wallet.get("name"), "address": address, "error": "invalid_wallet_address"})
            continue

        holdings: list[dict[str, Any]] = []
        for asset in network.get("assets", []):
            symbol = asset["symbol"]
            if asset["type"] == "native":
                raw = client.call("eth_getBalance", [address, "latest"])
                amount = to_decimal(raw, 18)
            else:
                token = asset.get("address", "")
                if not is_address(token):
                    holdings.append({"symbol": symbol, "error": "invalid_token_address", "amount": "0"})
                    continue
                raw = client.call("eth_call", [{"to": token, "data": encode_balance_of(address)}, "latest"])
                amount = to_decimal(raw, int(asset.get("decimals", 18)))

            holdings.append({"symbol": symbol, "amount": str(amount)})

        rows.append({"wallet": wallet.get("name"), "address": address, "holdings": holdings})
    return rows


def compute_pnl(rows: list[dict[str, Any]], pricing: dict[str, Any], baselines: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if row.get("error"):
            out.append(row)
            continue

        valuation = Decimal(0)
        for holding in row.get("holdings", []):
            price = Decimal(str(pricing.get(holding["symbol"], 0)))
            valuation += Decimal(holding["amount"]) * price

        base = Decimal(str((baselines.get(row["wallet"], {}) or {}).get("baseline_usd", 0)))
        pnl = valuation - base
        out.append(
            {
                **row,
                "valuation_usd": str(valuation),
                "baseline_usd": str(base),
                "pnl_usd": str(pnl),
            }
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="EVM PnL indexer")
    parser.add_argument("--config", default="Genesis-Conductor/ops/pnl_indexer.config.yml")
    parser.add_argument("--output", default="Genesis-Conductor/docs/pnl_status.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    endpoint = config["endpoint"]
    rpc_url = os.getenv(endpoint["env_rpc_url"], "")
    iam_token = os.getenv(endpoint["env_iam_token"], "")

    if not rpc_url and not args.dry_run:
        raise SystemExit(f"Missing RPC URL env: {endpoint['env_rpc_url']}")

    headers = {"content-type": "application/json"}
    if iam_token:
        headers["Authorization"] = f"Bearer {iam_token}"
        headers[endpoint.get("iam_header", "x-block6-iam")] = iam_token

    results = []
    for network in config.get("networks", []):
        if args.dry_run:
            wallets = [{"wallet": w.get("name"), "address": w.get("address"), "error": "dry_run"} for w in network.get("wallets", [])]
        else:
            client = RpcClient(rpc_url, headers, int(endpoint.get("timeout_seconds", 20)))
            wallets = fetch_balances(client, network)
            wallets = compute_pnl(wallets, config.get("pricing_usd", {}), config.get("baselines", {}))

        results.append(
            {
                "network": network.get("name"),
                "chain_id": network.get("chain_id"),
                "wallets": wallets,
            }
        )

    output = {
        "mode": "dry_run" if args.dry_run else "live",
        "rpc_env": endpoint["env_rpc_url"],
        "generated": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"pnl-indexer: wrote {output_path}")


if __name__ == "__main__":
    main()
