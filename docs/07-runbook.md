# 07 — Runbook (stand it up + go live)

This template validates and unit-tests out of the box, but running it for real
needs a Hermes install with profiles, auth, and scouts. This is the setup
sequence. `python -m cli.triage scaffold` prints these commands tailored to your
`triage.yaml`.

> Commands assume the `hermes` CLI and your per-profile wrappers are on PATH. On
> WSL, run them in your Linux shell (Hermes runs in WSL, even if the repo lives on
> a Windows drive).

## 1. Prerequisites

- Hermes installed and working (`hermes --version`).
- `pip install -r requirements.txt` in this repo (PyYAML).
- `python -m cli.triage validate` is clean.

## 2. Create the board

```bash
hermes kanban boards create <board>     # the `board:` from triage.yaml
```

## 3. Create the profiles

One profile per distinct value in `roles:` plus each `sources[].profile`. Clone
from a base profile, then set the model in each profile's `config.yaml`.

```bash
hermes profile create <name> --from <base>
# edit ~/.hermes/profiles/<name>/config.yaml → model: block (provider + model)
```

Multi-model is fine: e.g. one scout on one provider, the rest on another. The
profile is where the model is bound; the engine doesn't care.

## 4. Scout profiles need the `kanban` toolset

Scouts run via cron (not the dispatcher), so kanban tools aren't auto-enabled.
For each `sources[].profile`:

```yaml
# ~/.hermes/profiles/<scout>/config.yaml
toolsets: [hermes-cli, kanban]
```

Also ensure scouts have a web-search backend (a Tavily/Serper/Brave key in their
`.env`, or the built-in `web` toolset) so they can actually search.

## 5. Install the skills

- Copy `skills/templates/triage-orchestrator/` to the orchestrator profile's
  skills dir.
- Copy `skills/templates/triage-scout/` once per source to that source's profile,
  renamed to `sources[].skill`, with the source's `query` filled in.

## 6. Auth

Log in each profile's provider once (interactive, human-run). OAuth token stores
are **per profile** — logging in one profile doesn't cover another.

## 7. Configure the gate channel

For Telegram: set `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS=<your id>`, and a
home channel/thread in the orchestrator profile's `.env`. Message the bot once
(bots can't DM a user who hasn't started them). Verify delivery:

```bash
orchestrator send --to telegram "triage engine: delivery check"
```

## 8. Register the scout crons — in the GATEWAY profile's store

The gateway's cron ticker reads **only the gateway profile's** cron store. Run the
gateway under the orchestrator and register the scout jobs there with a run-under
profile (don't create them under the scout profiles' own stores — they'd list but
never fire).

```bash
orchestrator cron create '<schedule>' --profile <scout-profile> --skill <scout-skill>
# (confirm exact flags for your Hermes version)
orchestrator cron list --all          # both jobs present
orchestrator cron pause <id>          # keep paused until you go live
```

## 9. Start the runtime

The dispatcher + cron live inside the gateway. On WSL use foreground `run` (the
`start` subcommand wants an installed systemd service WSL often lacks). Keep it in
tmux/screen.

```bash
orchestrator gateway run               # foreground; dispatcher covers all boards
orchestrator gateway status            # → running (from another shell)
```

## 10. Smoke-test one cycle (before autonomous cron)

Trigger a scout by hand so you don't wait for the cron tick:

```bash
<scout-profile> chat --skills <scout-skill> -q "Run one sweep now, following the skill exactly."
hermes kanban --board <board> list     # watch cards appear + promote
```

Expected flow: `intake → (dedup/score) → research lanes (parallel) → route →
prep → propose` → **proposal DM** → you reply `approve <slug>` → `fulfill chain`
→ deliverable DM. Confirm the first post-gate card is `ready` (not `todo`).

## 11. Go live

```bash
orchestrator cron resume <scout-id>    # start with one scout
# watch a real cycle, then resume the others
```

The gateway must stay running for cron to fire and the board to dispatch.

## Day-to-day

- **Watch:** `hermes kanban --board <board> list`. Progress also DMs to you.
- **Decide:** reply (no slash) `approve <slug>` / `shelve <slug>: reason` /
  `modify <slug>: change`; `reject the rest` (or `python proposal_actions.py
  shelve-all`) clears the queue.
- **Cost:** `python scripts/cost_report.py <slug> --gate <usd>`.
- **Stop:** Ctrl-C the gateway.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Scout runs, no card appears | Scout profile missing `kanban` toolset (step 4). |
| Crons never fire | Jobs not in the gateway profile's store; recreate with `--profile` (step 8). |
| Card stuck in `todo` | It has an unfinished parent. Don't parent the first post-gate task to the triage card. |
| Proposal status set but no DM | Orchestrator didn't `hermes send`; status ≠ delivery (docs/05). |
| `/approve` "unknown command" | Telegram reserves `/`; reply without the slash. |
| Final delivery can't find artifacts | A stage used scratch, not the persistent `dir` workspace. |
| `gateway start` fails on WSL | Use `gateway run` (foreground). |
