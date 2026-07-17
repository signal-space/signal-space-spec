# signal-space-spec

Canonical schemas, fixtures, and conformance rules for Signal Space.

Signal Space is the shared surface layer for live signal graphs. It describes
graph topology, timelines, inspectors, decisions, and structured intents without
owning the source runtime or mutation authority.

## Scope

- `schemas/signal-space.schema.json` defines the versioned surface contract.
- `fixtures/` contains stable graph examples used by every implementation.
- `conformance/` defines fixture naming, version support, and validation rules.
- `docs/authority-boundaries.md` documents advisory and gated intent handling.
- `docs/binding-contract.md` defines the multi-language implementation contract.

## Dependency Direction

Signal Space implementations may depend on their matching `lazily-*` runtime
binding. The spec does not depend on agent-doc, patchboard, or any product
adapter. Product adapters project their private runtime state into the shared
surface shape and validate every mutation through their own authority boundary.

## Current Version

The current schema version is `0.4.0`. Fixtures use stable names and declare the
schema version they target:

- `agent_doc_supervisor.json` (stays at `0.2.0` as the backward-compatibility
  baseline)
- `patchboard_attention_router.json` (`0.4.0`)
- `patchboard_io_rack.json` (`0.4.0`)
- `patchboard_supervisor.json` (`0.4.0`)
- `patchboard_webhook_triage.json` (`0.4.0`)
- `patchboard_scheduled_anomaly.json` (`0.4.0`)
- `patchboard_event_fanout.json` (`0.4.0`)

`0.4.0` adds two optional graph-level fields, backward compatible with `0.3.0`:

- **Template metadata** — `category` (string) and `tags` (array of strings) on
  `SignalGraph`. Product adapters use `category` (conventionally
  `"workflow_template"`) plus `tags` to catalog reusable n8n-style workflow
  templates that wire ingress triggers, a learnable mixer, a deterministic gate,
  an agent node, and egress actions. See
  [`docs/workflow-templates.md`](docs/workflow-templates.md) for the concept map
  between n8n nodes and Signal Space primitives. The fields are descriptive
  catalog metadata only; they carry no authority and change no invariants.

`0.3.0` adds three optional surfaces, all backward compatible with `0.2.0`:

- **Typed ports** — `PortSpec` on `SignalNode`
  (`{ id, name, direction: in|out, dtype, required }`) and edge
  `from_port`/`to_port`. Edges that name their jacks are dtype-checked: the
  `from` jack must be an output, the `to` jack an input, and the dtypes must
  match. This is the "patch cable" contract the patchboard UI renders.
- **Stream telemetry** — `StreamTelemetry` on `SignalEdge`
  (`rate_hz`, `latency_ms`, `freshness_ms`, `last_value_preview`,
  `distribution_hint`, `missing_data`). The live-cable readout, declared as
  deterministic derived state (never a writable cell); connector failures
  surface as `missing_data` / stale freshness.
- **I/O bindings** — `IoBinding` on `SignalNode`
  (`{ direction: ingress|egress, transport, endpoint, format, schema_ref,
  auth_ref }`). Declares how a node binds to the outside world. Secrets are
  never inlined — `auth_ref` names a host-resolved credential. Ingress bindings
  are restricted to `source` nodes; egress bindings to `gate`/`output` nodes;
  egress never carries `direct` authority.

`0.2.0` added the optional `state_chart` field on `SignalNode`. The chart mirrors
lazily's `StateMachine<S, E>`: a list of `states`, an `initial` state, an
optional `current` state, and `transitions` of `{from, event, to}`. Events
conventionally match intent types so a `SurfaceIntent` doubles as a
state-machine event; the owning adapter still decides whether to apply the
transition at its authority boundary. Bindings that target `0.1.0` continue to
validate documents that do not use `state_chart`.

Implementation repositories should declare the supported spec version and prove
that these fixtures parse, validate, and round-trip without adding product-owned
fields to the core schema.

## Conformance Check

Run the canonical schema and fixture invariant checks with:

```bash
make check
```

The check validates every required fixture against
`schemas/signal-space.schema.json` and enforces the initial cross-fixture
invariants from `conformance/manifest.json`.

When the sibling implementation repositories are checked out beside the spec,
validate their version and lazily dependency metadata with:

```bash
make check-local-bindings
```
