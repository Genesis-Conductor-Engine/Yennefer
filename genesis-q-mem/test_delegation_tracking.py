import pytest
import sqlite3
import os
import uuid
from datetime import datetime

# Set environment variable before any imports
# This ensures SWARM_CONFIG picks up the test database path
os.environ["SWARM_DB_PATH"] = "test_delegations.db"

# Now import the modules that use SWARM_CONFIG
from swarm_api import init_db
from swarm_admin import delegation_count

@pytest.fixture
def setup_db():
    # Clean up before test
    if os.path.exists("test_delegations.db"):
        os.remove("test_delegations.db")

    # Initialize DB (creates table)
    init_db()

    yield

    # Clean up after test
    if os.path.exists("test_delegations.db"):
        os.remove("test_delegations.db")

@pytest.mark.asyncio
async def test_delegation_tracking_logic(setup_db):
    conn = sqlite3.connect("test_delegations.db")
    cursor = conn.cursor()

    # Verify table is initially empty
    cursor.execute("SELECT COUNT(*) FROM delegations")
    assert cursor.fetchone()[0] == 0

    # Insert a dummy delegation
    task_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO delegations (task_id, prompt, status, created_at, completed_at, cost_usd, tokens_used)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (task_id, "Test prompt", "completed", datetime.now(), datetime.now(), 0.01, 100))
    conn.commit()

    # Verify count via admin function
    # We call delegation_count directly. The dependency verify_admin is usually handled by FastAPI,
    # but here we can just pass the argument if needed.
    # delegation_count signature: (username: str = Depends(verify_admin))
    # We pass username="admin" manually.
    result = await delegation_count(username="admin")
    assert result == {"count": 1}

    # Insert another delegation
    task_id2 = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO delegations (task_id, prompt, status, created_at, completed_at, cost_usd, tokens_used)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (task_id2, "Test prompt 2", "completed", datetime.now(), datetime.now(), 0.02, 200))
    conn.commit()

    result = await delegation_count(username="admin")
    assert result == {"count": 2}

    conn.close()
