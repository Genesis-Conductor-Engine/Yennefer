import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from celestial_ingestion import IngestionError, ingest_repository




def test_ingest_repository_generates_required_fields(tmp_path: Path):
    repo = tmp_path / "orbit-agent"
    repo.mkdir()
    (repo / "README.md").write_text("Agent orchestration with security and integrity tests")
    (repo / "agent.py").write_text("print('hi')\n")
    (repo / "engine.rs").write_text("fn main() {}\n")

    result = ingest_repository(str(repo), {"active_agents": ["Codex"]})

    assert result["name"] == "orbit-agent"
    assert result["mass"] > 0
    assert result["gravity"]["language_diversity"] == 2
    assert result["seismic_test"]["schema_valid"] is True
    assert result["seismic_test"]["invariance_score"] == 1.0


def test_ingest_repository_rejects_missing_path():
    try:
        ingest_repository("/tmp/does-not-exist-123")
        assert False, "Expected IngestionError"
    except IngestionError:
        assert True
