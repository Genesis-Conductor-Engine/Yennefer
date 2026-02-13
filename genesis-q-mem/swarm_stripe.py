from typing import Dict, Any

SWARM_TIERS: Dict[str, Dict[str, Any]] = {
    "swarm_starter": {
        "price_id": "price_swarm_starter",
        "amount": 1999,  # $19.99/mo
        "currency": "usd",
        "features": {"max_monthly_tokens": 1_000_000, "max_workers": 3, "priority": "normal"},
    },
    "swarm_pro": {
        "price_id": "price_swarm_pro",
        "amount": 4999,  # $49.99/mo
        "currency": "usd",
        "features": {"max_monthly_tokens": 5_000_000, "max_workers": 5, "priority": "high"},
    },
    "swarm_enterprise": {
        "price_id": "price_swarm_enterprise",
        "amount": 19999,  # $199.99/mo
        "currency": "usd",
        "features": {"max_monthly_tokens": -1, "max_workers": 10, "priority": "critical"},  # unlimited
    },
}


def check_tier_limits(api_key: str, requested_tokens: int):
    """Check if user has quota for requested tokens"""
    # Query subscriptions.db for user tier
    import sqlite3
    from swarm_config import SWARM_CONFIG

    conn = sqlite3.connect(str(SWARM_CONFIG["database_path"]))
    cursor = conn.cursor()

    cursor.execute("SELECT tier FROM users WHERE api_key = ?", (api_key,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"allowed": False, "reason": "Invalid API key"}

    tier = str(row[0])
    if tier not in SWARM_TIERS:
        return {"allowed": False, "reason": "No swarm access"}

    max_tokens = SWARM_TIERS[tier]["features"]["max_monthly_tokens"]

    if max_tokens == -1:
        return {"allowed": True}

    # TODO: Track monthly usage
    return {"allowed": True, "remaining": max_tokens}
