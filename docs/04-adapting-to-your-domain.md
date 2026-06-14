# 04 — Adapting to your domain

This is the main "what do I do with this code" guide. It's written so an AI agent
can drive it with the human. Work top to bottom; validate after each step.

## Step 0 — Decide what your pipeline triages

Answer these with the human before editing anything:

1. **What is an "item"?** (a bug report, a sales lead, a support ticket, a content
   idea, a security finding, …)
2. **Where do items come from?** (which surfaces should scouts watch?)
3. **What makes an item worth acting on?** (the rubric)
4. **What's the routing decision?** (after research, what distinguishes the paths?)
5. **What does each path produce?** (the deliverable per outcome)
6. **What's the one thing the human approves?** (the gate)

These map 1:1 to `triage.yaml` blocks: sources, rubric, route, paths, gate.

## Step 1 — Rewrite `triage.yaml`

Edit in this order; run `python -m cli.triage validate` after each block.

1. **`name`, `board`, `workspace_root`, `cost_gate_usd`** — basic identity.
2. **`sources`** — one entry per scout. Set `profile`, `skill` (you'll create
   these in Step 4), `schedule`, and a precise `query`.
3. **`item_schema.fields`** — the fields scouts emit. Keep `title`, `claim`,
   `sources`; add domain fields your rubric/router need.
4. **`rubric`** — your dimensions, maxes, and threshold. Make the `hint`s concrete;
   the orchestrator scores from them.
5. **`research_lanes`** — the parallel investigations needed before routing. The
   `classifier_lane` is the one that emits the routing signal.
6. **`route.map`** — classification value → path name.
7. **`paths`** — one per route outcome. Define `prep`, `fulfill`, templates,
   workspace bucket, and (where relevant) `scope_rails` / `deliverable_spec`.
   Mark dead-end outcomes `auto: true`.
8. **`roles`** — map every role you used to a real profile name.
9. **`gate`** — reply verbs.

## Step 2 — Rewrite the path templates (`paths/`)

These markdown files are **inlined into worker task bodies** at runtime, so they
are how you control quality without editing code.

- `paths/rails/*.md` — **hard limits** for any "build/do work" path. Be strict;
  this is the safety boundary (docs/06).
- `paths/specs/*.md` — **output format** for any "produce an artifact" path
  (structure, style, quality bar). Point at a reference example if you have one.
- `paths/proposals/*.md` — the **gate message** for each path. Keep skimmable.

Name them to match the `scope_rails` / `deliverable_spec` / `template` paths you
set in `triage.yaml`.

## Step 3 — Choose your scoring mode

- **LLM mode (default, general):** the orchestrator scores each rubric dimension;
  the engine validates and applies the threshold. Works for any rubric — no code
  change. This is what the orchestrator skill uses.
- **Deterministic mode (optional):** `engine/scoring.py::score_candidate_heuristic`
  scores from structured fields with no model. It's keyed to the *reference*
  dimensions. If you keep it for a different rubric, **update its per-dimension
  rules** (it will note any dimension it doesn't recognize). Most adopters just
  use LLM mode and leave the heuristic as a test fixture.

## Step 4 — Rewrite the skills (`skills/templates/`)

- **Scout(s):** copy `triage-scout/SKILL.md` once per source, name each to match
  `sources[].skill`, and paste that source's `query` into "What to look for."
  Keep the report format in sync with `item_schema` and `intake_parser.py`.
- **Orchestrator:** `triage-orchestrator/SKILL.md` is already thin and
  config-driven. Adjust only the domain-flavored wording (what to dedup on, how to
  phrase proposals). Don't move deterministic logic back into it.

## Step 5 — Validate + test

```bash
python -m cli.triage validate            # config consistent?
python -m unittest discover -s tests     # engine still correct?
```

Add domain tests: a couple of scoring cases at/below your threshold, and a route
case per classification value. Copy the patterns in `tests/test_engine_core.py`.

## Step 6 — Stand it up

`python -m cli.triage scaffold` prints the Hermes commands to create the board,
profiles, skills, and crons. Then follow `docs/07-runbook.md` to set models/auth,
start the gateway, smoke-test one cycle, and go live.

## A worked mental model

Think of it as filling in blanks in one sentence:

> "Watch **\<sources\>** for **\<items\>**. Keep the ones that score ≥ **\<threshold\>**
> on **\<rubric\>**. After researching **\<lanes\>**, if **\<classifier\>** says
> **\<value\>**, do **\<path\>**, which produces **\<deliverable\>** — but only after
> I approve."

Every bolded blank is a `triage.yaml` value. Nothing there is code.
