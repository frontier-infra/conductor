# Hermes Multi-Agent Workflow

A reusable skeleton for an **autonomous, multi-agent triage pipeline** built on
[Hermes](https://github.com/NousResearch/hermes-agent): a fleet of agents that
**detects** items from sources, **dedups** them, **scores** them against a rubric,
**researches** them in parallel, **routes** each to a fulfillment path, pauses at
**one human approval gate**, then **fulfills and delivers** — all coordinated on a
single Hermes Kanban board.

It ships pre-wired as a worked example (find pain points AI-agent users hit →
build a fix or make an explainer video), so you can read a complete pipeline and
then repoint it at your own domain.

> **This is a template, not a turnkey app.** It runs its unit tests and validates
> its config out of the box, but going live requires setting up your Hermes
> install, profiles, auth, and scouts (see `docs/07-runbook.md`). The point is to
> give you — and your coding agent — a clear, working structure to adapt.

**Part of [Frontier Infra](https://github.com/frontier-infra) / The Machine.** Conductor is the
reference **ops driver** — **Box 2 (the Dumb Driver)** of The Machine, sibling of
[machine-driver](https://github.com/frontier-infra/machine-driver) (the *code-work* driver). Same
dumb-loop shape — durable state · fresh workers · verify-at-a-gate · propose-by-default — pointed
at a triage queue instead of a repo. It's a **starting point you adapt, not a turnkey product**.
Conformance: see [`CONFORMANCE.md`](./CONFORMANCE.md).

## The idea

```
sources → intake → dedup → score → research (parallel) → route
                                                            │
              ┌──────────────────────┬──────────────────────┤
            path A                 path B                  shelve
           (prep)                 (prep)                  (auto)
              └──────────┬───────────┘
                   ── HUMAN GATE ──   approve · shelve · modify
              ┌──────────┴───────────┐
            fulfill                fulfill
              └──────────┬───────────┘
                      deliver
```

The shape is fixed; **what flows through it is yours.** Everything domain-specific
lives in one file, `triage.yaml`.

## Quickstart

```bash
pip install -r requirements.txt          # just PyYAML
python -m cli.triage validate            # check the example config
python -m unittest discover -s tests     # 12 tests, all generic
python -m cli.triage scaffold            # print the Hermes setup plan
```

## Adapt it to your domain

The whole adaptation is editing `triage.yaml` + the markdown templates it points
at. Hand your coding agent **`AGENTS.md`** and ask it to walk you through
`docs/04-adapting-to-your-domain.md`. In brief:

1. Edit `triage.yaml`: sources, rubric, research lanes, route map, paths, roles.
2. Edit `paths/` templates (scope rails, deliverable specs, proposal formats).
3. Edit `skills/templates/` (scout queries + orchestrator notes).
4. `python -m cli.triage validate`, keep `tests/` green.
5. Follow `docs/07-runbook.md` to set up profiles and go live.

## Repository layout

```
triage.yaml              THE config — your whole pipeline (start here)
AGENTS.md                Guide for the AI agent adapting this template
engine/                  Generic engine (rarely edited)
  config.py              Loads + validates triage.yaml
  engine.py              TriageEngine — all deterministic step logic
  scoring.py             Rubric scoring (LLM mode + deterministic mode)
  routing.py             Classification → path
  dedup.py               Similarity (token-cosine; embedding-ready)
  item_vault.py          One markdown file per tracked item
  kanban_store.py        Writes the Hermes Kanban board
  intake_parser.py       Parses scout reports
  frontmatter.py         Stdlib YAML-frontmatter for item files
proposal_actions.py      Human-gate handler (approve/shelve/modify) — config-driven
paths/                   Per-path templates you customize
  rails/   specs/   proposals/
skills/templates/        Scout + orchestrator SKILL.md templates
cli/triage.py            validate / scaffold / init / install
scripts/cost_report.py   Per-item spend for the cost gate
tests/                   Generic engine tests
docs/                    Deep-dive docs (architecture, board, config, adapting, …)
examples/                Reference configs
```

## Documentation

- `docs/01-architecture.md` — fat engine / thin skill; how the pieces fit.
- `docs/02-the-board.md` — Kanban as the bus; dispatcher; fan-in.
- `docs/03-config-reference.md` — every `triage.yaml` key.
- `docs/04-adapting-to-your-domain.md` — the step-by-step adaptation guide.
- `docs/05-pipeline-stages.md` — each stage, and the gotchas to preserve.
- `docs/06-security.md` — trust surface, scope rails, safe publishing.
- `docs/07-runbook.md` — profiles, board, crons, go-live.
- `examples/ai-agent-pain-points/REFERENCE.md` — full write-up of the reference
  implementation this template was extracted from.

## Conformance

Conductor is a **reference template** for the ops driver in **The Machine** (the six-box harness)
— a running starting point you adapt, not a turnkey product. As shipped (the pain-points example)
it demonstrates **L3 — Enforced**: a non-bypassable human gate, **propose-by-default** (no side
effect until a human approves), a cost gate, and dedup. Emitting a signed **AAR** per approved
action via the org's [`aar.mjs`](https://github.com/frontier-infra/agentcontrolplane) reaches
**L4 — Receipted** — the same step the sibling
[machine-driver](https://github.com/frontier-infra/machine-driver) is taking. Conformance is a
property of *your wired deployment*; full mapping + caveats in [`CONFORMANCE.md`](./CONFORMANCE.md).

## Security

This template runs LLM-authored code and shells out, behind one human gate. Read
**`SECURITY.md`** and `docs/06-security.md` before deploying — and run the
pre-publish secret-scan checklist before open-sourcing an adapted copy.

## Contributing

See **`CONTRIBUTING.md`**. The golden rule: keep `engine/` domain-agnostic; new
domains go in `triage.yaml`, not the code.

## License

MIT — see `LICENSE`.

## Credits

Extracted and generalized from a working single-machine Hermes pipeline. The
engine is domain-agnostic; the bundled example reflects its origin.
