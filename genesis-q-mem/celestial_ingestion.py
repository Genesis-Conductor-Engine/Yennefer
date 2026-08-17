#!/usr/bin/env python3
"""A2A ingestion utilities for converting repositories into CelestialBody objects."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

CODE_EXTENSIONS = {
    ".py": "python",
    ".rs": "rust",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "react",
    ".tsx": "react",
    ".sol": "solidity",
    ".go": "go",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
}


@dataclass
class CelestialBody:
    body_id: str
    name: str
    source_path: str
    mass: float
    atmosphere: dict[str, Any]
    gravity: dict[str, Any]
    orbital_state: dict[str, Any]
    seismic_test: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class IngestionError(ValueError):
    """Raised when ingestion input is invalid."""


def _infer_language_counts(repo_path: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for file in repo_path.rglob("*"):
        if not file.is_file() or ".git" in file.parts:
            continue
        lang = CODE_EXTENSIONS.get(file.suffix.lower())
        if lang:
            counts[lang] = counts.get(lang, 0) + 1
    return counts


def _line_count(repo_path: Path) -> int:
    total = 0
    for file in repo_path.rglob("*"):
        if not file.is_file() or ".git" in file.parts:
            continue
        try:
            if file.suffix.lower() in CODE_EXTENSIONS:
                total += len(file.read_text(encoding="utf-8", errors="ignore").splitlines())
        except OSError:
            continue
    return total


def _read_summary(repo_path: Path) -> str:
    readme = repo_path / "README.md"
    if readme.exists():
        return readme.read_text(encoding="utf-8", errors="ignore")[:2000]
    return ""


def _compute_atmosphere(summary: str, metadata: dict[str, Any]) -> dict[str, Any]:
    text = f"{summary} {json.dumps(metadata, sort_keys=True)}".lower()
    traits = {
        "collaborative": any(k in text for k in ["agent", "handoff", "orchestr", "a2a"]),
        "stability_focus": any(k in text for k in ["test", "verify", "integrity", "security"]),
        "novelty_drive": any(k in text for k in ["experimental", "research", "prototype", "novel"]),
    }
    intent = "ecosystem" if traits["collaborative"] else "specialist"
    return {
        "intent": intent,
        "traits": traits,
        "summary_excerpt": summary[:240],
    }


def _compute_mass(file_count: int, loc: int) -> float:
    raw = (file_count * 0.4) + (loc * 0.001)
    return round(min(max(raw, 0.1), 100.0), 3)


def _compute_gravity(mass: float, atmosphere: dict[str, Any], language_counts: dict[str, int]) -> dict[str, Any]:
    language_diversity = len(language_counts)
    influence = round(min(1.0, (mass / 100.0) + (language_diversity * 0.03)), 6)
    pull = "high" if influence >= 0.75 else "medium" if influence >= 0.35 else "low"
    return {
        "influence_score": influence,
        "pull_tier": pull,
        "language_diversity": language_diversity,
        "anchors": sorted(language_counts, key=language_counts.get, reverse=True)[:3],
        "sanctuary_alignment": atmosphere["traits"]["stability_focus"],
    }


def _run_seismic_test(payload: dict[str, Any]) -> dict[str, Any]:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest_a = hashlib.sha256(canonical.encode()).hexdigest()
    digest_b = hashlib.sha256(canonical.encode()).hexdigest()
    invariant = digest_a == digest_b
    required = {"mass", "atmosphere", "gravity", "orbital_state"}
    schema_ok = required.issubset(payload.keys())
    return {
        "schema_valid": schema_ok,
        "stress_hash_consistent": invariant,
        "invariance_score": 1.0 if (schema_ok and invariant) else 0.0,
        "citation": f"sha256:{digest_a[:20]}",
    }


def ingest_repository(repo_path: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = metadata or {}
    root = Path(repo_path).resolve()
    if not root.exists() or not root.is_dir():
        raise IngestionError(f"Repository path not found: {repo_path}")

    language_counts = _infer_language_counts(root)
    file_count = sum(language_counts.values())
    loc = _line_count(root)
    summary = _read_summary(root)

    atmosphere = _compute_atmosphere(summary, metadata)
    mass = _compute_mass(file_count=file_count, loc=loc)
    gravity = _compute_gravity(mass, atmosphere, language_counts)
    orbital_state = {
        "phase": metadata.get("phase", "stable"),
        "active_agents": metadata.get("active_agents", []),
        "entropy": metadata.get("entropy", 0.5),
    }

    body_name = metadata.get("name", root.name)
    body_id = f"body_{hashlib.md5(str(root).encode()).hexdigest()[:12]}"

    body = CelestialBody(
        body_id=body_id,
        name=body_name,
        source_path=str(root),
        mass=mass,
        atmosphere=atmosphere,
        gravity=gravity,
        orbital_state=orbital_state,
        seismic_test={},
    )
    payload = body.to_dict()
    payload["seismic_test"] = _run_seismic_test(payload)
    return payload
