# Signal Space Conformance

Every implementation repo must declare a supported `signal-space-spec` version
and run the shared fixture set for that version.

## Fixture Names

Fixture names are stable API. A fixture may change only when its
`schema_version` changes or when the change is backwards-compatible for every
implementation that claims that version.

Required fixtures for `0.2.0`:

- `agent_doc_supervisor.json`
- `patchboard_attention_router.json`

The `0.2.0` fixtures use the optional `state_chart` field on some nodes; the
`agent_doc_supervisor` fixture remains `state_chart`-free to keep a minimal
baseline for `0.1.0`-only consumers.

## Required Checks

An implementation conforms to `0.2.0` when it can:

- parse every required fixture
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

## Version Semantics

Patch releases may add documentation or examples. Minor releases may add
optional fields or new intent modules. Major releases may rename fields, remove
fields, or change authority semantics.
