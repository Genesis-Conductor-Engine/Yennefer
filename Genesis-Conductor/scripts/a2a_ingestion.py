#!/usr/bin/env python3
"""A2A ingestion layer: transforms repo metadata into CelestialBody JSON objects."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class CelestialBody:
    id: str
    source_path: str
    body_type: str
    mass: int
    atmosphere: dict[str, Any]
    gravity: float
    seismic_test: dict[str, Any]
    generated_at: str


def estimate_mass(path: Path) -> int:
    if path.is_file():
        return max(1, path.stat().st_size // 256)
    files = [p for p in path.rglob("*") if p.is_file()]
    return max(1, sum(f.stat().st_size for f in files) // 512)


def estimate_atmosphere(path: Path) -> dict[str, Any]:
    ext_counts: dict[str, int] = {}
    files = [path] if path.is_file() else [p for p in path.rglob("*") if p.is_file()]
    for file_path in files:
        ext = file_path.suffix.lower() or "<none>"
        ext_counts[ext] = ext_counts.get(ext, 0) + 1

    intent = "execution" if any(ext in ext_counts for ext in (".py", ".rs", ".js", ".mjs")) else "archive"
    personality = "deterministic" if ".rs" in ext_counts else "adaptive"
    return {
        "intent": intent,
        "personality": personality,
        "dominant_extensions": sorted(ext_counts.items(), key=lambda i: i[1], reverse=True)[:5],
    }


def seismic_test(path: Path, mass: int) -> dict[str, Any]:
    # Structural truth under pressure: lightweight consistency checks.
    files = [path] if path.is_file() else [p for p in path.rglob("*") if p.is_file()]
    invariant_count = sum(1 for f in files if f.stat().st_size >= 0)
    pressure_score = min(1.0, invariant_count / 1000)
    return {
        "invariant_files": invariant_count,
        "pressure_score": pressure_score,
        "passed": mass > 0 and invariant_count > 0,
    }


def to_body(path: Path) -> CelestialBody:
    mass = estimate_mass(path)
    atmosphere = estimate_atmosphere(path)
    gravity = round(min(100.0, mass / 10), 2)
    seismic = seismic_test(path, mass)
    return CelestialBody(
        id=f"CB-{path.name.upper().replace('.', '-')}",
        source_path=str(path),
        body_type="agent_repo" if path.is_dir() else "artifact",
        mass=mass,
        atmosphere=atmosphere,
        gravity=gravity,
        seismic_test=seismic,
        generated_at=datetime.now(tz=timezone.utc).isoformat(),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert repos/files to CelestialBody JSON objects")
    parser.add_argument("inputs", nargs="+", help="Paths to files or repos")
    parser.add_argument("--output", default="Genesis-Conductor/docs/celestial_bodies.json")
    args = parser.parse_args()

    bodies = [asdict(to_body(Path(item).resolve())) for item in args.inputs]
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"bodies": bodies}, indent=2) + "\n", encoding="utf-8")

    print(f"a2a-ingestion: wrote {output_path} with {len(bodies)} celestial bodies")


if __name__ == "__main__":
    main()
