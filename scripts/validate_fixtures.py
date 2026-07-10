#!/usr/bin/env python3
"""Validate Signal Space schema fixtures and conformance invariants."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "signal-space.schema.json"
FIXTURES = [
    ROOT / "fixtures" / "agent_doc_supervisor.json",
    ROOT / "fixtures" / "patchboard_attention_router.json",
    ROOT / "fixtures" / "patchboard_io_rack.json",
    ROOT / "fixtures" / "patchboard_supervisor.json",
]

SUPPORTED_VERSIONS = {"0.2.0", "0.3.0"}
EGRESS_FAMILIES = {"gate", "output"}


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
    if document["schema_version"] not in SUPPORTED_VERSIONS:
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

    node_by_id = {node["id"]: node for node in nodes}
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
        chart = node.get("state_chart")
        if chart is not None:
            states = set(chart["states"])
            if chart["initial"] not in states:
                raise AssertionError(
                    f"{name}: state_chart initial not in states: {node['id']}"
                )
            if "current" in chart and chart["current"] not in states:
                raise AssertionError(
                    f"{name}: state_chart current not in states: {node['id']}"
                )
            for transition in chart["transitions"]:
                if transition["from"] not in states or transition["to"] not in states:
                    raise AssertionError(
                        f"{name}: state_chart transition out of bounds: {node['id']}"
                    )

        validate_ports(name, node)
        validate_io_binding(name, node)

    for edge in graph["edges"]:
        validate_edge_ports(name, edge, node_by_id)

    if graph["authority"]["default"] == "direct":
        raise AssertionError(f"{name}: fixture default authority must not be direct")

    classes = {event["state_class"] for event in graph["timeline"]}
    if not classes <= {"observation", "recommendation", "action"}:
        raise AssertionError(f"{name}: unknown timeline state class")


def validate_ports(name: str, node: dict[str, Any]) -> None:
    port_ids = [port["id"] for port in node.get("ports", [])]
    if len(port_ids) != len(set(port_ids)):
        raise AssertionError(f"{name}: duplicate port id on node {node['id']}")


def validate_io_binding(name: str, node: dict[str, Any]) -> None:
    binding = node.get("io_binding")
    if binding is None:
        return
    family = node["family"]
    if binding["direction"] == "ingress" and family != "source":
        raise AssertionError(
            f"{name}: ingress io_binding only allowed on source nodes: {node['id']}"
        )
    if binding["direction"] == "egress":
        if family not in EGRESS_FAMILIES:
            raise AssertionError(
                f"{name}: egress io_binding only allowed on gate/output nodes: {node['id']}"
            )
        if node["authority"]["default"] == "direct":
            raise AssertionError(
                f"{name}: egress io_binding cannot carry direct authority: {node['id']}"
            )


def validate_edge_ports(name: str, edge: dict[str, Any], node_by_id: dict[str, Any]) -> None:
    from_port_id = edge.get("from_port")
    if from_port_id is None:
        return
    to_port_id = edge.get("to_port")
    if to_port_id is None:
        raise AssertionError(
            f"{name}: edge names from_port but not to_port: {edge['id']}"
        )
    from_node = node_by_id[edge["from"]]
    to_node = node_by_id[edge["to"]]
    from_port = next((p for p in from_node.get("ports", []) if p["id"] == from_port_id), None)
    if from_port is None:
        raise AssertionError(f"{name}: edge from_port not found: {edge['id']}")
    to_port = next((p for p in to_node.get("ports", []) if p["id"] == to_port_id), None)
    if to_port is None:
        raise AssertionError(f"{name}: edge to_port not found: {edge['id']}")
    if from_port["direction"] != "out":
        raise AssertionError(f"{name}: edge from_port is not an output jack: {edge['id']}")
    if to_port["direction"] != "in":
        raise AssertionError(f"{name}: edge to_port is not an input jack: {edge['id']}")
    if from_port["dtype"] != to_port["dtype"]:
        raise AssertionError(
            f"{name}: edge port dtype mismatch ({from_port['dtype']} -> {to_port['dtype']}): {edge['id']}"
        )


def grants_direct(node: dict[str, Any], decision: dict[str, Any], intent: dict[str, Any]) -> bool:
    authority = node.get("authority") or {}
    return (
        authority.get("default") == "direct"
        or authority.get("by_intent", {}).get(intent.get("type")) == "direct"
        or decision.get("authority") == "direct"
    )


def validate_invalid_cases(validator: Any) -> None:
    base_document = json.loads(FIXTURES[0].read_text(encoding="utf-8"))
    patchboard = lambda: json.loads(FIXTURES[1].read_text(encoding="utf-8"))

    document = deepcopy(base_document)
    document["graph"]["nodes"][0]["id"] = "invalid id with spaces"
    assert_schema_invalid(
        "invalid_node_id",
        validator,
        document,
    )

    document = deepcopy(base_document)
    document["graph"]["nodes"][0]["state"]["fields"][0]["derived"] = True
    document["graph"]["nodes"][0]["state"]["fields"][0]["writable"] = True
    assert_invalid(
        "derived_field_writable",
        validator,
        document,
        "derived field is writable",
    )

    document = deepcopy(base_document)
    document["graph"]["edges"][0]["from"] = "missing.node"
    assert_invalid(
        "unknown_edge_endpoint",
        validator,
        document,
        "unknown endpoint",
    )

    document = patchboard()
    node = first_trainable_node(document)
    node["decision"]["capabilities"] = [
        capability
        for capability in node["decision"]["capabilities"]
        if capability != "trainable_model.lifecycle"
    ]
    assert_invalid(
        "trainable_lifecycle_without_capability",
        validator,
        document,
        "trainable lifecycle without decision capability",
    )

    document = deepcopy(base_document)
    intent = first_proposed_intent(document)
    intent["authority"] = "direct"
    assert_invalid(
        "direct_authority_escalation",
        validator,
        document,
        "direct authority",
    )

    document = patchboard()
    node = first_state_chart_node(document)
    node["state_chart"]["current"] = "missing_state"
    assert_invalid(
        "state_chart_current_out_of_bounds",
        validator,
        document,
        "state_chart current not in states",
    )

    document = patchboard()
    node = first_state_chart_node(document)
    node["state_chart"]["transitions"][0]["to"] = "missing_state"
    assert_invalid(
        "state_chart_transition_out_of_bounds",
        validator,
        document,
        "state_chart transition out of bounds",
    )

    # 0.3.0 invariants ------------------------------------------------------
    document = patchboard()
    ingress = node_by_id(document, "source.editor").pop("io_binding")
    node_by_id(document, "window.route_features")["io_binding"] = ingress
    assert_invalid(
        "ingress_binding_on_non_source",
        validator,
        document,
        "ingress io_binding only allowed on source",
    )

    document = patchboard()
    gate = node_by_id(document, "gate.approval")
    assert gate.get("io_binding") is not None
    gate["authority"]["default"] = "direct"
    assert_invalid(
        "egress_binding_direct_authority",
        validator,
        document,
        "egress io_binding cannot carry direct authority",
    )

    document = patchboard()
    events_in = next(
        p for p in node_by_id(document, "window.route_features")["ports"] if p["id"] == "events"
    )
    events_in["dtype"] = "scalar"
    assert_invalid(
        "edge_port_dtype_mismatch",
        validator,
        document,
        "edge port dtype mismatch",
    )

    document = patchboard()
    document["graph"]["edges"][0]["from_port"] = "imaginary"
    assert_invalid(
        "edge_from_port_not_found",
        validator,
        document,
        "edge from_port not found",
    )

    document = patchboard()
    source = node_by_id(document, "source.editor")
    source["ports"].append(deepcopy(source["ports"][0]))
    assert_invalid(
        "duplicate_port_id",
        validator,
        document,
        "duplicate port id",
    )


def node_by_id(document: dict[str, Any], node_id: str) -> dict[str, Any]:
    return next(node for node in document["graph"]["nodes"] if node["id"] == node_id)


def first_state_chart_node(document: dict[str, Any]) -> dict[str, Any]:
    for node in document["graph"]["nodes"]:
        if node.get("state_chart") is not None:
            return node
    raise AssertionError("fixture has no state_chart node")


def first_proposed_intent(document: dict[str, Any]) -> dict[str, Any]:
    for node in document["graph"]["nodes"]:
        decision = node.get("decision") or {}
        proposed_intents = decision.get("proposed_intents", [])
        if proposed_intents:
            return proposed_intents[0]
    raise AssertionError("fixture has no proposed intents")


def first_trainable_node(document: dict[str, Any]) -> dict[str, Any]:
    for node in document["graph"]["nodes"]:
        if "trainable_model.lifecycle" in node.get("allowed_modules", []):
            return node
    raise AssertionError("fixture has no trainable lifecycle node")


def assert_schema_invalid(
    name: str,
    validator: Any,
    document: dict[str, Any],
) -> None:
    try:
        validator.validate(document)
    except Exception:
        print(f"ok invalid {name}")
        return
    raise AssertionError(f"{name}: expected schema failure")


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
