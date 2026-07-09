# Signal Space Conformance

Every implementation repo must declare a supported `signal-space-spec` version
and run the shared fixture set for that version.

## Fixture Names

Fixture names are stable API. A fixture may change only when its
`schema_version` changes or when the change is backwards-compatible for every
implementation that claims that version.

Required fixtures for `0.3.0`:

- `agent_doc_supervisor.json` (kept at `0.2.0` — the backward-compatibility
  baseline; uses no `0.3.0` surfaces)
- `patchboard_attention_router.json` (`0.3.0` — typed ports, live cable
  telemetry, and one ingress + one egress webhook binding)
- `patchboard_io_rack.json` (`0.3.0` — exercises every `IoBinding` transport)

The `0.2.0` fixtures use the optional `state_chart` field on some nodes; the
`agent_doc_supervisor` fixture remains `state_chart`-free to keep a minimal
baseline for `0.1.0`-only consumers.

## Required Checks

An implementation conforms to `0.3.0` when it can:

- parse every required fixture (including the `0.2.0` baseline)
- validate node and edge ids
- reject edges whose endpoints are missing
- keep writable cell state separate from deterministic derived fields
- distinguish observation, recommendation, and action events
- expose intent modules without enabling trainable-model intents for fixed
  inference or agent-only nodes
- round-trip fixtures without losing graph, timeline, decision, authority, or
  intent envelope fields
- when `state_chart` is present, ensure `initial`, `current`, and every
  transition `from`/`to` reference declared states
- when `ports` are present, keep port ids unique within a node and dtype-check
  every cable that names `from_port`/`to_port` (out -> in, matching dtype)
- when `io_binding` is present, bind ingress to `source` nodes only, egress to
  `gate`/`output` nodes only, and never carry `direct` authority on egress

## Version Semantics

Patch releases may add documentation or examples. Minor releases may add
optional fields or new intent modules. Major releases may rename fields, remove
fields, or change authority semantics.
