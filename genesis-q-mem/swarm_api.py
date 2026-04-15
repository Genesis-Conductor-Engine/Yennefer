from fastapi import FastAPI, HTTPException
from swarm_orchestrator import SwarmOrchestrator
from swarm_models import SwarmTask, SwarmResult
import uuid
import sqlite3
from swarm_config import SWARM_CONFIG
from typing import Dict, Any, cast

app = FastAPI(title="Yennefer Swarm API")

orchestrator = SwarmOrchestrator()


def init_db():
    try:
        conn = sqlite3.connect(str(SWARM_CONFIG["database_path"]))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS delegations (
                task_id TEXT PRIMARY KEY,
                prompt TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                cost_usd REAL,
                tokens_used INTEGER
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database initialization failed: {e}")


@app.on_event("startup")
async def startup_event():
    init_db()


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "swarm_api"}


@app.post("/api/swarm/delegate", response_model=SwarmResult)
async def delegate(prompt: str, estimated_tokens: int = 10000):
    """Delegate task to Gemini swarm"""
    task = SwarmTask(
        task_id=str(uuid.uuid4()),
        prompt=prompt,
        complexity=min(10, estimated_tokens // 5000),
        estimated_tokens=estimated_tokens,
    )

    try:
        result = await orchestrator.delegate_task(task)

        # Save to DB
        try:
            conn = sqlite3.connect(str(SWARM_CONFIG["database_path"]))
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO delegations (task_id, prompt, status, completed_at, cost_usd, tokens_used)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (result.task_id, task.prompt, "completed", result.completed_at, result.cost_usd, result.tokens_used),
            )
            conn.commit()
            conn.close()
        except Exception as db_e:
            print(f"Failed to save delegation to DB: {db_e}")
            # Non-blocking failure for the main response

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/swarm/cost-estimate")
async def cost_estimate(tokens: int):
    """Estimate cost for token count"""
    cost_map = cast(Dict[str, float], SWARM_CONFIG["cost_per_1k_tokens"])
    cost = (tokens / 1000) * cost_map["flash"]
    return {
        "tokens": tokens,
        "cost_usd": cost,
        "savings_vs_claude": cost / 0.003,  # Claude Sonnet cost comparison
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8300)
