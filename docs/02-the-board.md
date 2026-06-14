# 02 — The board (how the fleet coordinates)

The pipeline has no message bus and no inter-agent chat. **The Hermes Kanban board
is the bus and the audit log.** Every unit of work is a card; every agent reads
and writes the same board.

## Cards and columns

A card (task) is mostly: a **title**, a **body** (instructions), an **assignee**
(which profile runs it), a **status** (`todo → ready → running → done`), and
optional **parent links**.

`engine/kanban_store.py` is the thin writer over the board's SQLite DB. You rarely
edit it.

## Assignee = routing

The whole multi-agent mechanism is a name on a card. A card assigned to `builder`
runs on the builder profile; one assigned to `video_producer` runs on that
profile. The engine maps abstract **roles** (in `triage.yaml`) to real **profiles**
via the `roles:` block, so your config talks in roles and the board gets profiles.

## The dispatcher

The Hermes **gateway** runs a dispatcher loop: it finds `ready` cards, claims one
atomically, spawns the assigned agent in its own workspace, and marks the card
`done` when the agent finishes — then repeats. It covers **all** boards. You don't
write this; you just keep the gateway running (`docs/07-runbook.md`).

## Fan-in (the part that makes it event-driven)

A card with parents starts in `todo` and **auto-promotes to `ready` only when
every parent is `done`.** That single rule gives you parallelism + sequencing with
no polling:

- The research lanes are all parented to the triage card → they run in parallel.
- A `route` card is parented to **all** the lanes → it fires the instant the last
  lane finishes.
- The post-gate fulfillment chain links each stage to the previous → they run in
  order.

`engine.research_specs()` and `engine.fulfillment_specs()` build exactly these
parent relationships. See the parent-linking in `proposal_actions.py::action_approve`.

## Two board gotchas the engine already handles

1. **First post-gate task must be `ready`, not `todo`.** If you parent the first
   fulfillment task to the still-open triage card, it waits forever (the triage
   card never completes). The handler creates the first stage with *no* parent
   (so it's `ready`) and chains the rest. Don't "fix" this by parenting it.

2. **`KanbanStore.create_task`** sets status from parents: none → `ready`, some →
   `todo`. That's the whole promotion contract; respect it when you create cards
   yourself.

## Dedicated board

Each pipeline uses its own board (`board:` in `triage.yaml`), isolated from
`default`, so triage cards don't mix with unrelated work. Named boards live at
`~/.hermes/kanban/boards/<slug>/kanban.db`; the back-compat `default` board is
`~/.hermes/kanban.db`. `proposal_actions.board_db()` resolves this for you and
honors the dispatcher-injected `HERMES_KANBAN_DB`.

## Version note

`kanban_store.py` writes the board schema directly (columns `id, title, body,
assignee, status, priority, created_by, created_at, workspace_kind,
workspace_path, consecutive_failures`, plus `task_links`, `task_comments`,
`task_events`). If a future Hermes release changes these, update the INSERTs
there. The dispatcher + cron live **inside the gateway** (the old standalone
`hermes kanban daemon` is deprecated).
