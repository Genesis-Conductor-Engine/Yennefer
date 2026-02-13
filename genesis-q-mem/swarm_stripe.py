import os
import datetime
import sqlite3

SWARM_TIERS = {
    "swarm_starter": {
        "price_id": "price_swarm_starter",
        "amount": 1999,  # $19.99/mo
        "currency": "usd",
        "features": {
            "max_monthly_tokens": 1_000_000,
            "max_workers": 3,
            "priority": "normal"
        }
    },
    "swarm_pro": {
        "price_id": "price_swarm_pro",
        "amount": 4999,  # $49.99/mo
        "currency": "usd",
        "features": {
            "max_monthly_tokens": 5_000_000,
            "max_workers": 5,
            "priority": "high"
        }
    },
    "swarm_enterprise": {
        "price_id": "price_swarm_enterprise",
        "amount": 19999,  # $199.99/mo
        "currency": "usd",
        "features": {
            "max_monthly_tokens": -1,  # unlimited
            "max_workers": 10,
            "priority": "critical"
        }
    }
}

DB_PATH = os.getenv("SWARM_DB_PATH", "/home/yenn/.yennefer/subscriptions.db")

def ensure_usage_table():
    """Ensure the usage_logs table exists"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT,
                tokens INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_usage_logs_api_key_timestamp
            ON usage_logs(api_key, timestamp)
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error ensuring usage table: {e}")

def get_monthly_usage(api_key: str) -> int:
    """Get total tokens used by an API key in the current month"""
    try:
        # Calculate start of month using timezone-aware UTC
        now = datetime.datetime.now(datetime.timezone.utc)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # SQLite stores datetimes as strings by default. Convert to ISO format explicitly.
        cursor.execute(
            "SELECT SUM(tokens) FROM usage_logs WHERE api_key = ? AND timestamp >= ?",
            (api_key, start_of_month.isoformat())
        )
        result = cursor.fetchone()[0]
        conn.close()

        return result if result else 0
    except Exception as e:
        print(f"Error getting monthly usage: {e}")
        return 0

def record_usage(api_key: str, tokens: int):
    """Record token usage for an API key"""
    try:
        ensure_usage_table()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Insert current UTC time as ISO string
        cursor.execute(
            "INSERT INTO usage_logs (api_key, tokens, timestamp) VALUES (?, ?, ?)",
            (api_key, tokens, datetime.datetime.now(datetime.timezone.utc).isoformat())
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error recording usage: {e}")

def check_tier_limits(api_key: str, requested_tokens: int):
    """Check if user has quota for requested tokens"""
    ensure_usage_table()

    # Query subscriptions.db for user tier
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT tier FROM users WHERE api_key = ?", (api_key,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {"allowed": False, "reason": "Invalid API key"}

        tier = row[0]
        if tier not in SWARM_TIERS:
            return {"allowed": False, "reason": "No swarm access"}

        max_tokens = SWARM_TIERS[tier]["features"]["max_monthly_tokens"]

        if max_tokens == -1:
            return {"allowed": True}

        current_usage = get_monthly_usage(api_key)
        remaining = max_tokens - current_usage

        if remaining < requested_tokens:
            return {
                "allowed": False,
                "reason": "Monthly limit exceeded",
                "remaining": remaining
            }

        return {"allowed": True, "remaining": remaining}

    except Exception as e:
        print(f"Error checking tier limits: {e}")
        return {"allowed": False, "reason": f"System error: {str(e)}"}
