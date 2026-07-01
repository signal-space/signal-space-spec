# Multi-Language Binding Contract

This contract defines what each Signal Space implementation must provide for a
given `signal-space-spec` version. The initial contract version is `0.1.0`;
`0.2.0` adds the optional `StateChart` surface described below.

## Required Repositories

The first implementation family is:

- `signal-space-rs`
- `signal-space-js`
- `signal-space-py`
- `signal-space-zig`
- `signal-space-kt`

Each implementation repository must declare:

- supported `signal-space-spec` version
- source repository for the spec
- dependency on the matching `lazily-*` binding
- conformance tests that parse and round-trip the canonical fixtures

## Required Types

Each binding must expose native representations for:

- `SignalGraph`
- `SignalNode`
- `SignalEdge`
- `SignalEvent`
- `TimelineEvent`
- `InspectorPanel` or an equivalent inspector view model
- `SurfaceIntent`
- `IntentSchema`
- `IntentModule`
- `DecisionEnvelope`
- `Authority`
- `StateChart` (added in `0.2.0`; optional on `SignalNode`)

The native names may follow language conventions, but the serialized form must
match `schemas/signal-space.schema.json`.

## State Charts

`0.2.0` introduces `StateChart` as an optional field on `SignalNode`. The shape
mirrors lazily's reactive `StateMachine<S, E>`:

- `states`: the enumeration of valid states (`S`)
- `initial`: the entry state
- `current`: optional live state (mirrors `StateMachine::state()`)
- `transitions`: declarative form of the transition function
  `Fn(&S, &E) -> Option<S>`, expressed as `{from, event, to}` triples

Bindings SHOULD construct a lazily `StateMachine` (or the matching lazily-* type
for the language) from a `StateChart` when a reactive runtime projection is
requested. The `event` strings conventionally match intent types advertised by
the graph so a `SurfaceIntent` doubles as a state-machine event; the binding
MUST still route every transition through the owning adapter's authority
boundary. Bindings that target only `0.1.0` MAY ignore the field.

## Validation Rules

Each binding must reject:

- unsupported `schema_version`
- duplicate node ids
- duplicate edge ids
- edges whose endpoints do not exist
- fields that are both `derived` and `writable`
- `trainable_model.lifecycle` modules on a decision without the matching
  capability
- authority transitions that silently upgrade advisory or gated intents to
  direct authority

A proposed `SurfaceIntent` may use `direct` authority only when the containing
decision, the target node's default authority, or the target node's per-intent
authority map explicitly grants `direct`. Advisory decisions may still propose
`gated` intents; the owning adapter remains responsible for applying or
rejecting them at its boundary.

## Lazily Relationship

The lazily dependency is the runtime contract for implementation repositories.
Bindings may keep core schema parsing independent of lazily so fixture tests are
cheap, but any runtime projection must use the matching lazily package:

- Rust: `lazily-rs`
- JavaScript: `lazily-js`
- Python: `lazily-py`
- Zig: `lazily-zig`
- Kotlin: `lazily-kt`

Runtime projections must keep writable cell state separate from deterministic
derived state. Snapshot/Delta exports are read-only mirrors unless the owning
adapter explicitly grants mutation authority.

## Product Boundary

No implementation binding may depend on agent-doc, patchboard, Signal Loops, or
another product adapter. Product adapters depend on Signal Space, project their
private runtime state into the shared surface shape, and validate every intent
through their own authority boundary.
