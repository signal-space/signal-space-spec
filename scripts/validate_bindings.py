#!/usr/bin/env python3
"""Validate local implementation metadata against the binding contract."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BINDINGS_PATH = ROOT / "conformance" / "bindings.json"


def main() -> int:
    manifest = json.loads(BINDINGS_PATH.read_text(encoding="utf-8"))
    failures: list[str] = []
    skipped: list[str] = []

    for binding in manifest["bindings"]:
        binding_root = (ROOT / binding["path"]).resolve()
        metadata_path = binding_root / binding["metadata_file"]
        if not metadata_path.exists():
            skipped.append(f"{binding['name']} missing at {binding_root}")
            continue

        metadata = metadata_path.read_text(encoding="utf-8")
        require_contains(
            failures,
            binding["name"],
            metadata_path,
            metadata,
            binding["spec_version_pattern"],
            "supported spec version",
        )
        for pattern in binding["lazily_dependency_patterns"]:
            require_contains(
                failures,
                binding["name"],
                metadata_path,
                metadata,
                pattern,
                "matching lazily dependency",
            )

        for pattern in binding["agent_doc_forbidden_patterns"]:
            if pattern in metadata:
                failures.append(
                    f"{binding['name']}: forbidden product dependency marker `{pattern}` found in metadata"
                )

        print(f"ok {binding['name']}")

    for message in skipped:
        print(f"skip {message}", file=sys.stderr)

    if failures:
        for failure in failures:
            print(f"error {failure}", file=sys.stderr)
        return 1

    return 0


def require_contains(
    failures: list[str],
    name: str,
    path: Path,
    text: str,
    pattern: str,
    description: str,
) -> None:
    if pattern not in text:
        failures.append(f"{name}: missing {description} `{pattern}` in {path}")


if __name__ == "__main__":
    raise SystemExit(main())
