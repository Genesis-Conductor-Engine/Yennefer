# Blockchain Tools API Reference

Complete API documentation for blockchain analytics tools.

## Overview

The Blockchain Tools API provides cryptocurrency wallet analytics, portfolio risk analysis, and gas fee optimization capabilities.

## Functions

### `query_wallet_balance()`

Query cryptocurrency balances for a wallet address.

```python
async def query_wallet_balance(
    address: str,
    chain: str = "ethereum",
    include_tokens: bool = True
) -> Dict[str, Any]
```

**Parameters:**
- `address` (required): Wallet address (0x...)
- `chain`: Blockchain network (default: "ethereum")
  - Options: `ethereum`, `polygon`, `arbitrum`, `optimism`, `base`
- `include_tokens`: Include ERC-20 token balances (default: True)

**Returns:**
```python
{
    "address": str,
    "chain": str,
    "native_balance": {
        "symbol": str,      # "ETH", "MATIC", etc.
        "balance": float,   # Native token balance
        "usd_value": float  # USD equivalent
    },
    "tokens": [
        {
            "symbol": str,
            "name": str,
            "address": str,
            "balance": float,
            "decimals": int,
            "usd_value": float,
            "price_change_24h": float
        }
    ],
    "total_usd_value": float,
    "last_updated": str  # ISO timestamp
}
```

**Example:**
```python
from src.blockchain_tools import query_wallet_balance

result = await query_wallet_balance(
    address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    chain="ethereum",
    include_tokens=True
)

print(f"Total portfolio value: ${result['total_usd_value']:,.2f}")

for token in result['tokens']:
    print(f"{token['symbol']}: {token['balance']} (${token['usd_value']:,.2f})")
```

**Errors:**
- `InvalidAddressError`: Invalid wallet address format
- `UnsupportedChainError`: Chain not supported
- `RPCError`: Blockchain RPC node error

---

### `analyze_portfolio_risk()`

Analyze risk metrics for a cryptocurrency portfolio.

```python
async def analyze_portfolio_risk(
    holdings: List[Dict[str, float]],
    risk_model: str = "monte_carlo",
    time_horizon: int = 30
) -> Dict[str, Any]
```

**Parameters:**
- `holdings` (required): List of token holdings
  ```python
  [
      {"symbol": "ETH", "amount": 10.5, "usd_value": 21000},
      {"symbol": "BTC", "amount": 0.5, "usd_value": 22500}
  ]
  ```
- `risk_model`: Risk calculation model
  - `monte_carlo`: Monte Carlo simulation (default)
  - `historical`: Historical volatility
  - `var`: Value at Risk
- `time_horizon`: Analysis period in days (default: 30)

**Returns:**
```python
{
    "risk_score": float,        # 0.0 (low) to 1.0 (high)
    "volatility": {
        "daily": float,         # Daily volatility %
        "annual": float         # Annualized volatility %
    },
    "diversification": {
        "score": float,         # 0.0 (concentrated) to 1.0 (diversified)
        "herfindahl_index": float,
        "top_3_concentration": float  # % in top 3 holdings
    },
    "var_95": float,            # Value at Risk (95% confidence)
    "cvar_95": float,           # Conditional VaR
    "sharpe_ratio": float,
    "max_drawdown": float,      # Maximum historical drawdown %
    "correlation_matrix": Dict[str, Dict[str, float]],
    "recommendations": List[str]
}
```

**Example:**
```python
holdings = [
    {"symbol": "ETH", "amount": 10.5, "usd_value": 21000},
    {"symbol": "BTC", "amount": 0.5, "usd_value": 22500},
    {"symbol": "USDC", "amount": 5000, "usd_value": 5000}
]

risk = await analyze_portfolio_risk(
    holdings=holdings,
    risk_model="monte_carlo",
    time_horizon=30
)

print(f"Risk Score: {risk['risk_score']:.2f}")
print(f"Annual Volatility: {risk['volatility']['annual']:.1f}%")
print(f"Diversification: {risk['diversification']['score']:.2f}")

for rec in risk['recommendations']:
    print(f"- {rec}")
```

---

### `simulate_rebalancing()`

Simulate portfolio rebalancing scenarios using Monte Carlo.

```python
async def simulate_rebalancing(
    current_allocation: Dict[str, float],
    target_allocation: Dict[str, float],
    simulations: int = 1000,
    time_horizon: int = 30
) -> Dict[str, Any]
```

**Parameters:**
- `current_allocation` (required): Current portfolio weights (symbol: weight)
  ```python
  {"ETH": 0.6, "BTC": 0.3, "USDC": 0.1}
  ```
- `target_allocation` (required): Target portfolio weights
  ```python
  {"ETH": 0.5, "BTC": 0.3, "USDC": 0.2}
  ```
- `simulations`: Number of Monte Carlo simulations (default: 1000)
- `time_horizon`: Simulation period in days (default: 30)

**Returns:**
```python
{
    "rebalancing_trades": [
        {
            "symbol": str,
            "action": str,      # "buy" | "sell"
            "amount": float,
            "usd_value": float
        }
    ],
    "expected_outcomes": {
        "mean_return": float,           # Expected return %
        "median_return": float,
        "std_deviation": float,
        "best_case": float,             # 95th percentile
        "worst_case": float,            # 5th percentile
        "probability_positive": float   # Probability of gain
    },
    "risk_metrics": {
        "current_risk": float,
        "target_risk": float,
        "risk_reduction": float         # % reduction
    },
    "cost_analysis": {
        "gas_fees": float,
        "slippage": float,
        "total_cost": float
    },
    "simulations": int,
    "convergence_analysis": {
        "energy_values": List[float],   # CUDA-Q energy convergence
        "optimal_params": Dict[str, float]
    }
}
```

**Example:**
```python
current = {"ETH": 0.7, "BTC": 0.2, "USDC": 0.1}
target = {"ETH": 0.5, "BTC": 0.3, "USDC": 0.2}

result = await simulate_rebalancing(
    current_allocation=current,
    target_allocation=target,
    simulations=1000,
    time_horizon=30
)

print("Rebalancing Trades:")
for trade in result['rebalancing_trades']:
    print(f"  {trade['action'].upper()} {trade['amount']:.4f} {trade['symbol']}")

print(f"\nExpected Return: {result['expected_outcomes']['mean_return']:.2f}%")
print(f"Risk Reduction: {result['risk_metrics']['risk_reduction']:.2f}%")
print(f"Total Cost: ${result['cost_analysis']['total_cost']:.2f}")
```

---

### `optimize_gas_fees()`

Optimize gas fees for Ethereum transactions.

```python
async def optimize_gas_fees(
    transaction_type: str,
    priority: str = "medium",
    max_wait_time: int = 300
) -> Dict[str, Any]
```

**Parameters:**
- `transaction_type` (required): Type of transaction
  - `transfer`: Simple ETH/token transfer
  - `swap`: DEX swap
  - `liquidity`: Add/remove liquidity
  - `nft`: NFT mint/transfer
- `priority`: Transaction priority
  - `low`: Cheapest, may take longer
  - `medium`: Balanced (default)
  - `high`: Fast, higher cost
- `max_wait_time`: Maximum wait time in seconds (default: 300)

**Returns:**
```python
{
    "recommended_gas": {
        "max_fee": float,           # Max fee per gas (gwei)
        "max_priority_fee": float,  # Priority fee (gwei)
        "gas_limit": int,
        "estimated_cost": {
            "eth": float,
            "usd": float
        }
    },
    "alternatives": [
        {
            "priority": str,
            "max_fee": float,
            "estimated_time": int,  # Seconds
            "estimated_cost": {
                "eth": float,
                "usd": float
            }
        }
    ],
    "network_conditions": {
        "base_fee": float,          # Current base fee (gwei)
        "congestion": str,          # "low" | "medium" | "high"
        "suggested_time": str       # Best time to transact
    },
    "savings_opportunity": {
        "potential_savings": float,  # USD
        "optimal_time": str          # ISO timestamp
    }
}
```

**Example:**
```python
gas = await optimize_gas_fees(
    transaction_type="swap",
    priority="medium",
    max_wait_time=300
)

rec = gas['recommended_gas']
print(f"Max Fee: {rec['max_fee']:.2f} gwei")
print(f"Estimated Cost: ${rec['estimated_cost']['usd']:.2f}")
print(f"Network Congestion: {gas['network_conditions']['congestion']}")

if gas['savings_opportunity']['potential_savings'] > 1:
    print(f"\nSave ${gas['savings_opportunity']['potential_savings']:.2f}")
    print(f"by waiting until {gas['savings_opportunity']['optimal_time']}")
```

---

### `get_token_metrics()`

Get detailed metrics for a specific token.

```python
async def get_token_metrics(
    symbol: str,
    chain: str = "ethereum"
) -> Dict[str, Any]
```

**Parameters:**
- `symbol` (required): Token symbol (e.g., "ETH", "UNI")
- `chain`: Blockchain network (default: "ethereum")

**Returns:**
```python
{
    "symbol": str,
    "name": str,
    "address": str,
    "price": {
        "usd": float,
        "change_24h": float,
        "change_7d": float,
        "change_30d": float
    },
    "market_data": {
        "market_cap": float,
        "volume_24h": float,
        "circulating_supply": float,
        "total_supply": float
    },
    "defi_metrics": {
        "tvl": float,               # Total value locked
        "liquidity": float,
        "holders": int
    },
    "technical_indicators": {
        "rsi_14": float,            # RSI (14-day)
        "ma_50": float,             # Moving average (50-day)
        "ma_200": float,            # Moving average (200-day)
        "volatility_30d": float
    }
}
```

---

## Integration with Claude

All blockchain tools are available as Claude tools:

```python
from src.orchestrator import ClaudeOrchestrator
from src.blockchain_tools import BLOCKCHAIN_TOOLS

orchestrator = ClaudeOrchestrator(api_key=api_key)

response = await orchestrator.chat(
    message="Analyze wallet 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb and suggest rebalancing",
    tools=BLOCKCHAIN_TOOLS
)
```

## Rate Limits

- **Wallet queries:** 60 requests/minute
- **Risk analysis:** 30 requests/minute
- **Rebalancing simulations:** 10 requests/minute (compute-intensive)
- **Gas optimization:** 60 requests/minute

## Error Handling

```python
from src.blockchain_tools.exceptions import (
    BlockchainError,
    InvalidAddressError,
    RPCError,
    RateLimitError
)

try:
    result = await query_wallet_balance(address="0x...")
except InvalidAddressError:
    print("Invalid wallet address")
except RPCError as e:
    print(f"RPC error: {e.message}")
except RateLimitError:
    print("Rate limit exceeded, retry after 60s")
```

## Configuration

```bash
# RPC Endpoints
ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/...
POLYGON_RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/...

# API Keys
ALCHEMY_API_KEY=...
ETHERSCAN_API_KEY=...
COINGECKO_API_KEY=...

# Settings
BLOCKCHAIN_CACHE_TTL=300
BLOCKCHAIN_TIMEOUT=30
```

## Related Documentation

- [Blockchain Tools Implementation](../guides/BLOCKCHAIN_TOOLS_IMPLEMENTATION.md)
- [CUDA-Q Integration](../guides/CUDA_Q_INTEGRATION.md)
- [Claude Orchestrator API](ORCHESTRATOR_API.md)

---

**Last updated:** 2025-05-12
