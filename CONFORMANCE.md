# Conductor Conformance

Conductor is a **reference template** for the **ops driver** in
[The Machine](https://github.com/frontier-infra) — the six-box harness for reliable long-running
intelligence — and the sibling of [machine-driver](https://github.com/frontier-infra/machine-driver)
(the *code* driver). It is **extracted and generalized from a working Hermes pipeline**: a clear,
running *starting point* you adapt to your own domain, **not a turnkey production system**. The
bundled example is the **ai-agent-pain-points** pipeline — scouts find pain points AI-agent users
hit, and each is routed to *build a fix* or *make an explainer video*, behind one human gate.

This file assesses **what the skeleton demonstrates as shipped**. Conformance is a property of a
*wired* deployment, not of a template — when you repoint Conductor at your domain, re-run the
evidence below and re-assess your own level.

## As shipped (the bundled example): **L3 — Enforced**

Ladder: L0 Look-Alike · L1 Declared · L2 Instrumented · **L3 Enforced** · L4 Receipted ·
L5 Trusted Autonomy. Out of the box the skeleton **blocks at a non-bypassable human gate, takes no
side effect until that gate approves (propose-by-default), caps cost, and dedups** — the
L3-Enforced shape, demonstrated. It is **not L4**: the generic skeleton records its decisions in
the item vault and on the board, but it does **not yet emit a signed AAR** per action via the
canonical `aar.mjs`.

## The six boxes → the code

| Box | Obligation | In Conductor | Status |
|---|---|---|---|
| **0 Contracted Decomposition** | define what's "worth doing" + in/out of scope before work | `triage.yaml` rubric (ship at 65/100) + `paths/rails/build.md` (what may be built) + `paths/specs/video.md` (deliverable format) | **Declared** — config-as-contract; no independent `ratified_by` yet |
| **1 Durable Goal + State** | state lives outside any session | the Hermes **Kanban board** (`engine/kanban_store.py`) + `engine/item_vault.py` (one markdown file per item) | **Pass** |
| **2 Dumb Driver** | deterministic control; model only where judgment is needed | **fat engine** (`engine/engine.py` — dedup/score-math/route/chain-build, unit-tested with no model) / **thin skill** (`skills/templates/triage-orchestrator` — judgment-only: score dims, classify, propose prose) | **Enforced (calibrated)** — the deterministic core is token-free; the orchestrator spends tokens only on the fuzzy steps. The spec's Box-2 calibration, not the zero-token ideal. |
| **3 Fresh Workers** | ephemeral, per-task workers | scouts (detect, cron) · parallel research lanes · prep/fulfill chains — each a fresh task | **Pass** |
| **4 Verify vs Reality** | independent verification against ground truth; `verifier ≠ subject` | **human gate** (`proposal_actions.py`: approve/shelve/modify) — the approver is not the agent that drafted, and it refuses to act unless the item is `awaiting_approval`; the scout pulls a **verbatim** quote from the live source as ground truth | **Enforced**; **no AAR emitted yet** → L4 on emitting + signing one |
| **5 Autonomy Dial** | earned, scoped, non-bypassable | **propose-by-default** (`agents.yaml` modes off/dry-run/live; the detect→propose loop runs dry-run, fulfillment workers stay `off` until armed); **`cost_gate_usd`**; the one human gate is the only path to a side effect | **Enforced** (fail-closed) |

## Cross-cutting obligations

| Obligation | In Conductor | Status |
|---|---|---|
| **Cost Governor** | `cost_gate_usd` + `scripts/cost_report.py` (per-item spend) | **Pass** |
| **Idempotency** | `engine/dedup.py` (no duplicate items at intake) | **Pass at intake**; a per-action receipt/idempotency ledger is part of the L4 work below |
| **Quarantine** | `shelve` route — below-threshold items auto-shelve and `good` (already-served) items are shelved, never forced through | **Pass** |
| **Escalation** | the human gate via `hermes send` → Telegram (status fields don't notify; delivery is explicit) | **Pass** |
| **Observability** | Kanban board + item vault (one markdown file per item, scored breakdown and path recorded) | **Pass** |
| **AAR receipts** | not emitted by the generic skeleton | **Pending (L4)** |

## Evidence (run it, don't trust it)

```bash
python -m cli.triage validate          # the contract (triage.yaml) is well-formed
python -m unittest discover -s tests    # 12 generic engine tests (config / scoring / routing / specs)
```

## → L4 (Receipted)

At the gate, emit a per-action **AAR** — claim · verdict · idempotency key — and sign it with the
org's canonical signer ([`agentcontrolplane/tools/aar.mjs`](https://github.com/frontier-infra/agentcontrolplane)).
The generic skeleton ships the gate and the ground truth but **not** an AAR writer, so reaching L4
here means *emitting* the record and then signing it. This is the **same iteration the sibling
[machine-driver](https://github.com/frontier-infra/machine-driver) is taking** — both drivers sit at
L3 today and reach L4 by receipting what they verify. They differ only in domain: ops vs code.
