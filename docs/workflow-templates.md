# Workflow Templates

Signal Space graphs can catalog themselves as reusable **workflow templates** so
product adapters (the patchboard first) can ship n8n-style automation recipes
that additionally route signals through agents, multi-layer perceptrons, and
outside services — all under the same auditable authority model.

This document is the canonical mapping between n8n concepts and Signal Space
primitives, plus the rules a template must follow.

## Template metadata (0.4.0)

A graph opts into the template catalog with two optional `0.4.0` fields on
`SignalGraph`:

| Field | Type | Purpose |
|-------|------|---------|
| `category` | `string?` | Catalog bucket. Convention: `"workflow_template"` for an n8n-style template. |
| `tags` | `string[]` | Free-form descriptors of triggers, actions, and intent (e.g. `"trigger:webhook"`, `"action:exec"`, `"mlp"`, `"agent"`). |

These fields are **descriptive catalog metadata only**. They carry no authority
and change no invariants; a graph that omits them validates identically. The
graph still owns its `authority` block, and every external effect is still
gated.

## n8n → Signal Space concept map

n8n is a node-based automation tool: trigger nodes produce events, logic nodes
route them, action nodes reach the outside world, and AI/ML nodes reason or
classify. Every one of those maps onto an existing Signal Space primitive.

| n8n concept | Signal Space primitive | Notes |
|-------------|------------------------|-------|
| **Trigger** (Webhook, Schedule/Cron, Form, Manual) | `source` node + ingress `IoBinding` | `transport: webhook` / `timer` / `file_tail` / `stdin_jsonl` / `websocket`. The trigger is read-only observation — `local` authority, never `direct`. |
| **HTTP Request** / **action node** | `output` node + egress `IoBinding` | `transport: webhook` / `exec` / `notify` / `mcp`. Egress only on `gate`/`output`, never `direct`. |
| **IF / Switch / Merge** (routing logic) | `transform` node, or `decision` node with `mode: deterministic` | Deterministic routing lives in the graph, not in an opaque node. |
| **Code / Function** node | `transform` node (`mode: rolling_window`, map, filter) | Pure shaping; `local` authority. |
| **ML / classification** node | `decision` node with `mode: model` | The learnable mixer (logistic or **MLP**). Advisory by default; promote/rollback are `gated` through `trainable_model.lifecycle`. |
| **AI Agent** / **Advanced AI** node | `decision` node with `mode: small_agent` / `large_agent` | Slow reasoning node. Receives a bounded packet, returns an **advisory** plan/intent — never `direct`. |
| **Workflow** (the whole canvas) | `SignalGraph` | `category: "workflow_template"` + `tags` catalog it. |
| **Execution / execution data** | `timeline` + `recent_events` | Observation / recommendation / action state classes keep the loop auditable. |
| **Credentials** | `auth_ref` on the `IoBinding` | Secrets are host-resolved, **never inlined** in the graph. |

### What the patchboard adds beyond stock n8n

A plain n8n workflow is fire-and-forget: a trigger runs an action. A patchboard
template inserts three signal layers between trigger and action:

1. **A feature window** (`transform`, rolling window) — turns raw events into an
   observed feature vector, with live cable telemetry.
2. **A learnable mixer** (`decision`, `mode: model`, an **MLP**) — scores whether
   this situation deserves an action, trainable from timeline labels via
   replay → shadow → gated promote.
3. **A gate + an agent** (`gate` + `decision` `small_agent`/`large_agent`) — the
   deterministic gate holds every external effect until approved; the agent only
   runs when the gate *would* release, proposing an advisory intent rather than
   executing.

So the canonical template shape is:

```text
trigger (source, ingress) -> feature window (transform)
                           -> learnable mixer (decision, model = MLP)
                           -> approval gate (gate)
                           -> agent (decision, small_agent | large_agent)
                           -> action(s) (output, egress)
```

The result is n8n-style automation that *learns from feedback* and *defers to a
human before any external effect*, instead of firing actions blindly.

## Template catalog

These `0.4.0` fixtures are `category: "workflow_template"`:

| Fixture | n8n shape | Triggers → Actions | Signals |
|---------|-----------|--------------------|---------|
| `patchboard_webhook_triage.json` | Webhook → workflow → HTTP | webhook → **webhook** | MLP anomaly + small_agent |
| `patchboard_scheduled_anomaly.json` | Schedule → workflow → Notify | timer + file_tail → **notify** | MLP anomaly + large_agent |
| `patchboard_event_fanout.json` | Webhook → Switch → fan-out | websocket → **webhook + exec + mcp** | deterministic switch + MLP router |

## Rules for authoring a template

1. **Category + tags.** Set `category: "workflow_template"` and tag the graph's
   triggers (`trigger:<transport>`), actions (`action:<transport>`), and signal
   layers (`mlp`, `agent`, `switch`).
2. **Ingress is observation.** Every trigger is a `source` with an ingress
   `IoBinding` and `local` authority. Ingress bindings only ever attach to
   `source` nodes.
3. **Egress is gated.** Every action is a `gate` or `output` with an egress
   `IoBinding`. Egress authority is `gated` (or `advisory` for an MCP agent
   trigger) — **never `direct`**. Validation rejects a direct-authority egress.
4. **No secrets in the document.** External credentials are named by `auth_ref`
   and resolved by the host.
5. **Learned state is inspectable.** A model node advertises
   `trainable_model.lifecycle` in both `allowed_modules` and its decision
   `capabilities`, so replay/shadow/promote are auditable on the timeline.
6. **Agents propose, they do not execute.** An agent node's
   `proposed_intents` target the gate or an output with `advisory`/`gated`
   authority. The deterministic gate and an approved intent remain between any
   learned output and an external effect.
7. **Cables are typed.** Edges that name `from_port`/`to_port` must connect an
   output jack to an input jack with matching `dtype`. This is the patch-cable
   contract the UI renders and the validator enforces.

## Adding a new template

1. Author a fixture under `fixtures/` declaring `schema_version: "0.4.0"`,
   `category: "workflow_template"`, and tags; validate it with
   `python3 scripts/validate_fixtures.py`.
2. Register it in `conformance/manifest.json` and (if a binding round-trips it)
   the binding's conformance test.
3. In the patchboard, add a pure builder that constructs the same graph and a
   parity test that the builder and the fixture agree (see `docs/recipes.md`).
