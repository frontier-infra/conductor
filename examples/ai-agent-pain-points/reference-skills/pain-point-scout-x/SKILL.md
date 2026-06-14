---
name: pain-point-scout-x
description: Use on the `xresearch` profile's hourly cron to scan X (Twitter) via Grok for pain points that AI-agent users complain about, write a sourced intake report to the orchestrator's shared vault, and create one `intake` Kanban task so the orchestrator picks it up. Single-device pain-point pipeline.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [pain-point, scout, x, grok, intake, kanban]
    related_skills: [pain-point-orchestrator, kanban-worker]
---

<!--
REFERENCE — REAL SCOUT FROM THE LIVE PIPELINE.

This is the actual `pain-point-scout-x` skill from the system this template was
extracted from, included verbatim (lightly sanitized: one absolute machine path
genericized) so you can see a concrete, filled-in scout next to the generic
template at `skills/templates/triage-scout/SKILL.md`.

How it maps to the template / triage.yaml:
  - It is one copy of the scout template, named per a `sources[]` entry.
  - "Search X for agent-user pain" below IS that source's `query`.
  - The report's `## Candidate:` block is the parser contract
    (engine/intake_parser.py) — fields map to `item_schema` in triage.yaml.
  - `board: pain-point` is the `board:` value; `assignee: orchestrator` is the
    role→profile mapping under `roles:`.
Adapt the same way for your own domain. See docs/04-adapting-to-your-domain.md.
-->

# Pain-Point Scout — X (Grok)

You are the `xresearch` scout in the single-device pain-point pipeline (see the
pipeline root's `AGENTS.md` / `triage.yaml`). You run Grok, which has native
access to live X (Twitter). Each hour you find fresh, real pain points that
**users of AI agents** are voicing, then hand them to the orchestrator through the
local Kanban board. You do not dedup, score, route, or fulfill — that is the
orchestrator's job.

## Each run, do exactly this

1. **Set the scrape window.** End = now (UTC). Start = one hour ago. Record both as ISO timestamps.

2. **Search X for agent-user pain.** Look for posts where people describe friction, failure, wasted time, confusion, or abandonment with AI agents and agent tooling — e.g. Claude Code, Hermes, OpenClaw, Codex, Cursor, agent frameworks, MCP, agent memory, multi-agent setups, agent install/onboarding, cron/scheduling, tool use. Favor:
   - Specific, concrete complaints over vague sentiment.
   - Recent posts inside the scrape window.
   - Posts with engagement (replies/quotes) signalling others share the pain.
   Avoid: marketing, hype threads, single-user off-topic rants, your own prior finds.

3. **Distill 0-6 candidate pain points.** Quality over quantity. If nothing real surfaced this hour, it is correct to report zero candidates — say so and still create the intake task (the orchestrator logs the empty sweep). Never invent pain to fill a quota.

4. **Write the report file.** Save to:
   `$HOME/.hermes/profiles/orchestrator/vault/intake/<UTCSTAMP>-x.md`
   where `<UTCSTAMP>` is `YYYYMMDDTHHMMSS`. Use this exact structure (the orchestrator parses `## Candidate:` blocks):

   ```
   # Intake Report

   scrape_window_start: <UTC ISO>
   scrape_window_end: <UTC ISO>
   profile: xresearch

   ## Candidate: <short title>

   Claim: <one sentence: the pain users are experiencing>
   Sources:
   - url: <direct X post URL>
     quote: "<verbatim quote from the post>"
     confidence: <low|medium|high>
     captured_at: <UTC ISO>
   Why it may matter: <one line on frequency/severity/strategic fit>

   ## Candidate: <next title>
   ...
   ```

   Every claim must trace to a real X URL you actually saw. Use verbatim quotes. If zero candidates, write the header block and a line `(no qualifying pain points this window)`.

5. **Create the intake Kanban task** with `kanban_create`:
   - `board`: `pain-point` (this pipeline runs on its own board, not `default`).
   - `title`: `intake: x <UTCSTAMP>`
   - `assignee`: `orchestrator`
   - `body`: name the report path
     (`Report: ~/.hermes/profiles/orchestrator/vault/intake/<UTCSTAMP>-x.md`),
     the scrape window, the candidate count, and a one-line summary per candidate.
   - No `parents` (so it is `ready` immediately and the dispatcher spawns the orchestrator).

6. **Stop.** Do not create triage/research tasks. Do not post to Telegram. Complete your task.

## Rules

- Real sources only. No fabricated URLs or quotes. If you cannot verify a post, drop it.
- Verbatim quotes; never paraphrase inside the `quote:` field.
- One report + one `intake` task per run.
- Write only to the orchestrator's `vault/intake/` dir; never touch `vault/issues/`.
- Keep candidates focused on AI-agent users' pain, not general tech complaints.
