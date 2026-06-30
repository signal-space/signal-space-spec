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

The initial schema version is `0.1.0`. Fixtures use stable names and declare the
schema version they target:

- `agent_doc_supervisor.json`
- `patchboard_attention_router.json`

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
