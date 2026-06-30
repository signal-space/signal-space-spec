#!/usr/bin/env python3
"""Validate Signal Space schema fixtures and conformance invariants."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "signal-space.schema.json"
FIXTURES = [
    ROOT / "fixtures" / "agent_doc_supervisor.json",
    ROOT / "fixtures" / "patchboard_attention_router.json",
]


def main() -> int:
    try:
        import jsonschema
    except ImportError:
        print("missing dependency: install jsonschema to run conformance checks", file=sys.stderr)
        return 2

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)

    for fixture_path in FIXTURES:
        document = json.loads(fixture_path.read_text(encoding="utf-8"))
        validator.validate(document)
        validate_invariants(fixture_path.name, document)
        print(f"ok {fixture_path.name}")

    return 0


def validate_invariants(name: str, document: dict) -> None:
    if document["schema_version"] != "0.1.0":
        raise AssertionError(f"{name}: unsupported schema_version")

    graph = document["graph"]
    nodes = graph["nodes"]
    node_ids = [node["id"] for node in nodes]
    if len(node_ids) != len(set(node_ids)):
        raise AssertionError(f"{name}: duplicate node ids")

    edge_ids = [edge["id"] for edge in graph["edges"]]
    if len(edge_ids) != len(set(edge_ids)):
        raise AssertionError(f"{name}: duplicate edge ids")

    node_id_set = set(node_ids)
    for edge in graph["edges"]:
        if edge["from"] not in node_id_set or edge["to"] not in node_id_set:
            raise AssertionError(f"{name}: edge has unknown endpoint: {edge['id']}")

    for node in nodes:
        for field in node["state"]["fields"]:
            if field.get("derived", False) and field["writable"]:
                raise AssertionError(f"{name}: derived field is writable: {field['id']}")
        if "trainable_model.lifecycle" in node.get("allowed_modules", []):
            decision = node.get("decision") or {}
            if "trainable_model.lifecycle" not in decision.get("capabilities", []):
                raise AssertionError(
                    f"{name}: trainable lifecycle without decision capability: {node['id']}"
                )

    if graph["authority"]["default"] == "direct":
        raise AssertionError(f"{name}: fixture default authority must not be direct")

    classes = {event["state_class"] for event in graph["timeline"]}
    if not classes <= {"observation", "recommendation", "action"}:
        raise AssertionError(f"{name}: unknown timeline state class")


if __name__ == "__main__":
    raise SystemExit(main())
