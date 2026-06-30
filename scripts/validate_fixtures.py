#!/usr/bin/env python3
"""Validate Signal Space schema fixtures and conformance invariants."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


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

    validate_invalid_cases(validator)
    return 0


def validate_invariants(name: str, document: dict[str, Any]) -> None:
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
        decision = node.get("decision") or {}
        for intent in decision.get("proposed_intents", []):
            if intent.get("authority") == "direct" and not grants_direct(node, decision, intent):
                raise AssertionError(
                    f"{name}: proposed intent silently upgrades to direct authority: {intent['id']}"
                )

    if graph["authority"]["default"] == "direct":
        raise AssertionError(f"{name}: fixture default authority must not be direct")

    classes = {event["state_class"] for event in graph["timeline"]}
    if not classes <= {"observation", "recommendation", "action"}:
        raise AssertionError(f"{name}: unknown timeline state class")


def grants_direct(node: dict[str, Any], decision: dict[str, Any], intent: dict[str, Any]) -> bool:
    authority = node.get("authority") or {}
    return (
        authority.get("default") == "direct"
        or authority.get("by_intent", {}).get(intent.get("type")) == "direct"
        or decision.get("authority") == "direct"
    )


def validate_invalid_cases(validator: Any) -> None:
    document = json.loads(FIXTURES[0].read_text(encoding="utf-8"))
    intent = first_proposed_intent(document)
    intent["authority"] = "direct"
    assert_invalid(
        "direct_authority_escalation",
        validator,
        document,
        "direct authority",
    )


def first_proposed_intent(document: dict[str, Any]) -> dict[str, Any]:
    for node in document["graph"]["nodes"]:
        decision = node.get("decision") or {}
        proposed_intents = decision.get("proposed_intents", [])
        if proposed_intents:
            return proposed_intents[0]
    raise AssertionError("fixture has no proposed intents")


def assert_invalid(
    name: str,
    validator: Any,
    document: dict[str, Any],
    expected: str,
) -> None:
    validator.validate(document)
    try:
        validate_invariants(name, document)
    except AssertionError as error:
        if expected not in str(error):
            raise
        print(f"ok invalid {name}")
        return
    raise AssertionError(f"{name}: expected invariant failure")


if __name__ == "__main__":
    raise SystemExit(main())
