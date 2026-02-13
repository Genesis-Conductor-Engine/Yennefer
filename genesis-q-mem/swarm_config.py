import os
import pathlib

SWARM_CONFIG = {
    "project_id": os.getenv("GCP_PROJECT_ID", "yenn-484707"),
    "location": "us-central1",
    "supervisor_model": "gemini-2.0-flash-exp",
    "worker_model": "gemini-2.0-flash-exp",
    "max_workers": 5,
    "worker_timeout": 300,
    "cost_per_1k_tokens": {"flash": 0.00015, "pro": 0.00125},  # $0.15 per 1M tokens  # $1.25 per 1M tokens
    "database_path": os.getenv("SWARM_DB_PATH", str(pathlib.Path.home() / ".yennefer/subscriptions.db")),
}

_default_creds = pathlib.Path.home() / ".config/gcloud/application_default_credentials.json"
VERTEX_AI_CREDS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", str(_default_creds))
