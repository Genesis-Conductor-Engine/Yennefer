from __future__ import annotations

import json
import os
import pathlib
import subprocess
import tempfile
import urllib.error
import urllib.request
from urllib.parse import urlencode

from mcp.server.fastmcp import FastMCP

API_BASE = os.environ.get("POSTMAN_API_BASE", "https://api.getpostman.com")
KEY_STORE = pathlib.Path(os.environ.get("POSTMAN_KEY_FILE", "/private/var/root/.openkey"))
POSTMAN_CLI = os.environ.get("POSTMAN_CLI", "postman")

mcp = FastMCP("postman")


def _api_key() -> str:
    key = os.environ.get("POSTMAN_API_KEY")
    if key:
        return key.strip()
    if KEY_STORE.exists():
        return KEY_STORE.read_text().strip()
    raise RuntimeError("POSTMAN_API_KEY is not set and no key store was found")


def _api(path: str, **query) -> dict:
    url = f"{API_BASE}{path}"
    if query:
        url += "?" + urlencode(query)
    req = urllib.request.Request(url, headers={"X-Api-Key": _api_key()})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Postman API error {e.code}: {e.read().decode()[:500]}") from e


@mcp.tool()
def postman_health() -> str:
    """Validate that the Postman API key works. Returns account info and key status."""
    try:
        data = _api("/me")
        u = data["user"]
        return (
            f"ok: authenticated as {u.get('fullName') or u.get('username') or u.get('id')} "
            f"(team {u.get('teamName')}, roles {u.get('roles')})"
        )
    except RuntimeError as e:
        return f"unauthenticated: {e}"


@mcp.tool()
def postman_list_workspaces() -> str:
    """List Postman workspaces visible to the API key."""
    data = _api("/workspaces")
    ws = data.get("workspaces", [])
    if not ws:
        return "no workspaces found"
    return json.dumps(
        [{"id": w["id"], "name": w["name"], "type": w.get("type")} for w in ws],
        indent=2,
    )


@mcp.tool()
def postman_list_collections(workspace_id: str | None = None) -> str:
    """List Postman collections. Optionally narrow to one workspace_id."""
    data = _api("/collections", workspace=workspace_id) if workspace_id else _api("/collections")
    cols = data.get("collections", [])
    if not cols:
        return "no collections found"
    return json.dumps(
        [{"id": c["uid"], "name": c["name"], "owner": c.get("owner")} for c in cols],
        indent=2,
    )


@mcp.tool()
def postman_get_collection(collection_uid: str) -> str:
    """Fetch the full definition of a collection by its uid (e.g. 1234567-abcdef...)."""
    data = _api(f"/collections/{collection_uid}")
    col = data.get("collection", {})
    return json.dumps({"name": col.get("info", {}).get("name"), "collection": col}, indent=2)


@mcp.tool()
def postman_list_environments() -> str:
    """List Postman environments visible to the API key."""
    data = _api("/environments")
    envs = data.get("environments", [])
    if not envs:
        return "no environments found"
    return json.dumps(
        [{"id": e["uid"], "name": e["name"], "owner": e.get("owner")} for e in envs],
        indent=2,
    )


@mcp.tool()
def postman_get_environment(environment_uid: str) -> str:
    """Fetch an environment (variables) by its uid."""
    data = _api(f"/environments/{environment_uid}")
    env = data.get("environment", {})
    return json.dumps(
        {
            "id": env.get("id"),
            "name": env.get("name"),
            "values": [
                {"key": v.get("key"), "value": v.get("value"), "enabled": v.get("enabled")}
                for v in env.get("values", [])
            ],
        },
        indent=2,
    )


@mcp.tool()
def postman_run_collection(
    collection_uid: str, environment_uid: str | None = None, timeout_seconds: int = 180
) -> str:
    """Run a Postman collection locally with the Postman CLI and return the report.

    Uses `postman collection run` (no cloud/Pro plan needed). The collection and
    optional environment are fetched via the API into temp files first.
    """
    col = _api(f"/collections/{collection_uid}").get("collection", {})
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(col, f)
        col_path = f.name
    env_path = None
    if environment_uid:
        env = _api(f"/environments/{environment_uid}").get("environment", {})
        slim = {"name": env.get("name"), "values": env.get("values", [])}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(slim, f)
            env_path = f.name
    cmd = [POSTMAN_CLI, "collection", "run", col_path, "-r", "cli"]
    if env_path:
        cmd += ["-e", env_path]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout_seconds
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return f"exit={proc.returncode}\n{out[-8000:]}"
    except subprocess.TimeoutExpired:
        return f"collection run timed out after {timeout_seconds}s"
    finally:
        for p in (col_path, env_path):
            if p:
                os.unlink(p)


if __name__ == "__main__":
    mcp.run()
