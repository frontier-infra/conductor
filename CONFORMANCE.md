# Conductor Conformance

Conductor is a **reference template** for the **ops driver** in
[The Machine](https://github.com/frontier-infra) — the six-box harness for reliable long-running
applied intelligence — and the sibling of [machine-driver](https://github.com/frontier-infra/machine-driver)
(the *code* driver). It is **extracted and generalized from a working Hermes pipeline**: a clear,
running *starting point* you adapt to your own domain, **not a turnkey production system**. The
bundled example is the **ai-agent-pain-points** pipeline — scouts find pain points AI-agent users
hit, and each is routed to *build a fix* or *make an explainer video*, behind one human gate.

This file is the honest self-assessment; the **kit is the source of truth — run it, don't trust
this prose**. Conformance is a property of a *wired* deployment, not of a template — when you
repoint Conductor at your domain, re-run the kit and re-assess your own level.

## Level: **L2 Instrumented** (kit-measured, vNext)

Run the executable kit instead of arguing a level:

```bash
cd <frontier-infra>/the-machine && python3 -m kit score <…>/conductor
```

It scores Conductor at **L2 Instrumented (strict)** against **The Machine — Conformance Spec
vNext** (ratified 2026-06-14). The Enforced *shape* is demonstrated — a non-bypassable human gate,
propose-by-default (no side effect until approval), fail-closed verify (`verifier ≠ subject`),
terminal quarantine, and a cost cap — and several of those rows **PASS at L3** (Box 4 verify,
Box 0 independent ratification, terminal quarantine, agent-contract caps). But the **overall level
is gated at L2** because vNext raised the L3 bar to also require **Δ1 reversibility**, **Δ2
operator-override**, **Δ3 runtime-health**, append-only audit hooks, and an enforced autonomy
ceiling — all of which the kit flags FAIL — and several controls remain **PARTIAL** (contract
enforced as downgrade-to-propose, not hard-deny at the driver; no explicit
`min(operator, ceiling, trust)` dial; alert without ACK; idempotency without cross-store dedup).
Honest reading: Conductor demonstrates the Enforced controls but **sits at L2** until those L3 rows
clear — the same ladder the sibling [machine-driver](https://github.com/frontier-infra/machine-driver)
is climbing (it reached L2 plus signed-AAR receipts in iteration 2).

## The six boxes → the code (kit-cited)

| Box | Obligation | In Conductor | Kit |
|---|---|---|---|
| **0 Contracted Decomposition** | scope + rubric ratified before work, by a ratifier ≠ proposer | `triage.yaml` rubric + `paths/rails/build.md` + `paths/specs/video.md`; `ratified_by: frontier-infra council` (independent of the proposer) | **PASS** (incl. L3 independent ratification) |
| **1 Durable Goal + State** | state outlives the session; survives kill | Hermes **Kanban board** (`engine/kanban_store.py`) + `engine/item_vault.py` (atomic `os.replace`, one md file per item) | **PASS** |
| **2 Dumb Driver** | deterministic control; model only where judgment is needed | **fat engine** (`engine/engine.py` — dedup/score/route/chain, unit-tested with no model) / **thin skill** (judgment-only) | **PASS** |
| **3 Fresh Workers** | ephemeral, per-task workers | scouts · parallel research lanes · prep/fulfill chains — each a fresh task | **PASS** |
| **4 Verify vs Reality** | independent ground-truth verify; `verifier ≠ subject`; fail-closed | **human gate** (`proposal_actions.py` — refuses unless the item is `awaiting_approval`); the scout pulls a **verbatim** quote from the live source as ground truth | **PASS (L3)** |
| **5 Autonomy Dial** | `min(operator, ceiling, trust)`; reversibility-aware; non-bypassable | **propose-by-default** (`agents.yaml` off/dry-run/live); `cost_gate_usd`; the one human gate is the only path to a side effect | **PARTIAL** — no explicit `min()` dial; **Δ1 reversibility FAIL** |

## Cross-cutting (kit-cited)

| Obligation | In Conductor | Kit |
|---|---|---|
| **Cost / Resource Governor** | `cost_gate_usd` + `scripts/cost_report.py` (per-item spend) | **PARTIAL** — envelope declared; breach → halt not shown |
| **Idempotency** | `engine/dedup.py` (no duplicate items at intake) | **PARTIAL** — key/similarity present; cross-store duplicate-rejection not shown |
| **Terminal Quarantine** | `shelve` route — off-scope / below-threshold items shelved, not re-queued | **PASS (L3)** |
| **Agent Contracts (caps)** | `cost_gate_usd` as a pre-mutation check | **PASS (L3)** |
| **Observability / Escalation** | human gate via `hermes send` → Telegram | **PARTIAL** — alerting present, no alert-with-ACK |
| **Non-bypassability** | the single human gate is the only path to a side effect | **PARTIAL** — intent present; needs a chaos bypass probe |
| **AAR receipts (signed)** | not emitted by the generic skeleton | **FAIL** — the L3 → L4 line |
| **Operator override · Audit hooks · Autonomy ceiling · Runtime-health (Δ2, Δ3)** | not yet built (pre-iteration-2) | **FAIL** — the vNext L3 gates |

## Evidence (run it, don't trust it)

```bash
python -m cli.triage validate          # the contract (triage.yaml) is well-formed
python -m unittest discover -s tests    # generic engine tests (config / scoring / routing / specs)
cd <frontier-infra>/the-machine && python3 -m kit score <…>/conductor   # the level, scored from code
```

## Path up: L2 → L3 → L4

**To L3 (Enforced):** add the vNext Δ controls the kit flags — a **reversibility term** in the gate
(Δ1), a **non-bypassable operator override with a bound SLO** (Δ2), **runtime-health** (a
`last_success_at` heartbeat plus an independent staleness monitor and registered anomaly detectors,
Δ3), **append-only chained audit receipts**, an enforced **autonomy ceiling**, and harden
contract-enforcement from downgrade-to-propose into a **hard-deny at the driver**.

**To L4 (Receipted):** emit a per-action **AAR** — claim · verdict · idempotency key — and **sign**
it with the org's canonical signer ([`aar.mjs`](https://github.com/frontier-infra/agentcontrolplane)).
This is the **same iteration the sibling [machine-driver](https://github.com/frontier-infra/machine-driver)
has already taken** (signed AAR, L4-ready receipts); both drivers differ only in domain: ops vs code.
