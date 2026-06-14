# 06 — Security & safe publishing

This pipeline runs **LLM-authored code** (any build path), **shells out**, and
acts **autonomously** between scouting and the gate. Treat it like the powerful,
dual-use tool it is. This doc is the trust surface and the rules for publishing
your adapted version.

## The trust surface (say this plainly in your README)

- **Scouts** fetch untrusted web content. That content becomes task bodies a model
  reads → classic prompt-injection surface. Don't let scout output drive
  privileged actions without the gate and the scope rails in between.
- **The build path** can have an agent write and run code. The **scope rails**
  (`paths/rails/*.md`) are the boundary on what it may build. Keep them tight and
  specific; an empty or vague rails file is an open door.
- **Shell + delivery.** The orchestrator runs shell commands and sends messages
  to the human. Restrict the profiles' toolsets to what each role needs.
- **One human gate.** It exists to bound cost and to keep a person between research
  and fulfillment. **Never make it auto-approve.**

## Scope rails are the safety mechanism

The single most important security control here is the per-path rails file. Good
rails enumerate *acceptable* targets and an explicit *never* list (see the
shipped `paths/rails/build.md`). When a proposal doesn't fit, the rule is
**shelve or re-route — never widen the rails to fit.**

## Secrets: what must NEVER be committed

The `.gitignore` excludes these; verify before any push:

- `.env`, `*.env` — API keys, tokens, web-search keys.
- `auth.json` / any OAuth token store.
- `*.db` / `*.sqlite*` — board databases (contain your real items + history).
- `work/`, `vault/`, `intake/` — generated items, scout reports, deliverables.
- Anything under per-profile Hermes dirs.

Use `.env.example` (committed, no values) to document required variables.

## What's safe to publish

- The `engine/` package, `proposal_actions.py`, `cli/`, `scripts/`, `tests/`.
- `triage.yaml` (config, no secrets) and the `paths/` + `skills/templates/`
  markdown — **review them first** for anything domain-confidential (internal
  URLs, customer names, private endpoints in your `query` strings).
- `docs/`, `README.md`, `AGENTS.md`, `LICENSE`.

## Pre-publish checklist

1. `git status` / `git ls-files` — confirm no `.env`, `*.db`, `auth.json`, `work/`.
2. Grep the tree for secrets: tokens, keys, internal hostnames, personal handles.
3. Read every `query:` in `triage.yaml` and every `paths/`/`skills/` file for
   confidential domain detail.
4. Confirm the README states the trust surface (the bullets above).
5. Confirm the scope rails are real, not the placeholder.
6. Run a static secret-scanner if you have one.

## Operational hardening

- Give each profile the **minimum toolset** for its role. Only the orchestrator
  needs Telegram; scouts need web + `kanban`; workers need only what they build
  with.
- Keep the **cost gate** on; it's a spend circuit-breaker, not just telemetry.
- Prefer **read-only** scouting. The detection half should never mutate anything.
