# Authority Boundaries And Advisory Intents

Signal Space describes possible state changes; it does not apply them.

The owning runtime or product adapter is always responsible for validating,
applying, rejecting, queueing, auditing, or asking for approval for a
`SurfaceIntent`.

## Authority Levels

- `local`: view-only interaction such as selection, focus, filtering, and
  opening inspectors.
- `advisory`: a request or recommendation that the owner may ignore or convert
  into a product-specific operation.
- `gated`: a request that requires an explicit policy check, approval, budget,
  lease, or single-writer guard before it can affect product state.
- `direct`: a request that the owner has explicitly granted permission to apply
  without another approval step.

Adapters should default to `local`, `advisory`, or `gated`. A graph, node, or
module should advertise `direct` only when the owner can prove the caller is
inside the correct authority boundary.

## Product Boundaries

Agent-doc owns markdown parsing, closeout, `finalize`, `session-check`, writes,
commits, and binary-owned mutation authority. Its Signal Space projection must
remain read-only or advisory until agent-doc applies the mutation itself.

Patchboard and Signal Loops own realtime execution, model lifecycle, approvals,
and external effects. Signal Space can expose model candidates, labels,
rollback metadata, and proposed agent actions, but the patchboard adapter keeps
the gate policy and effect authority.

A node MAY declare a `state_chart` (added in `0.2.0`) so inspectors can show
valid transitions and so `SurfaceIntent`s can double as state-machine events.
The chart only describes possible transitions; the patchboard adapter still owns
whether to apply, queue, or reject each event at its authority boundary.

## MCP Boundary

The MCP server is a control plane for inspection, schema discovery, validation,
preview, fixture export, and intent submission. It is not the high-frequency
Snapshot/Delta data plane. Realtime renderers may consume app-native streams
while still using Signal Space for stable surface shape and intent envelopes.
