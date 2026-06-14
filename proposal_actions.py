#!/usr/bin/env python3
"""Human-gate action handler — approve / shelve / modify, fully config-driven.

The orchestrator shells out to this when the human replies at the gate. It reads
the post-gate chain from `triage.yaml` (`paths.<path>.fulfill`), so you do NOT
edit this file to add or reorder stages — you edit the YAML.

    python proposal_actions.py approve     <slug>
    python proposal_actions.py shelve      <slug> [--reason "..."]
    python proposal_actions.py shelve-all  [--except <slug>] [--reason "..."]
    python proposal_actions.py modify      <slug> --change "..."

Reply syntax note (Telegram): the human replies with NO leading slash —
`approve <slug>` — because Telegram intercepts `/commands`. The orchestrator maps
the reply verbs (see `gate:` in triage.yaml) to these subcommands.

Environment overrides:
    TRIAGE_CONFIG          path to triage.yaml          (default: ./triage.yaml)
    TRIAGE_VAULT_DIR       items vault dir              (default: <workspace_root>/vault/items)
    HERMES_KANBAN_DB       board DB (dispatcher injects it for workers)

Stdlib + PyYAML (for config) + local `engine/*` only, so it runs from a thin shell.
It refuses to act unless the item status is `awaiting_approval`.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from engine.config import TriageConfig
from engine.engine import TriageEngine
from engine.item_vault import ItemVault, utc_now_iso
from engine.kanban_store import KanbanStore

CONFIG_PATH = Path(os.environ.get("TRIAGE_CONFIG") or "triage.yaml")
EXPECTED_STATUS = "awaiting_approval"


def load_config() -> TriageConfig:
    return TriageConfig.load(CONFIG_PATH)


def vault_dir(config: TriageConfig) -> Path:
    env = os.environ.get("TRIAGE_VAULT_DIR")
    if env:
        return Path(env).resolve()
    return (Path(config.workspace_root).resolve() / "vault" / "items")


def board_db(config: TriageConfig) -> Path:
    """Resolve the board DB the same way Hermes does.

    The dispatcher injects HERMES_KANBAN_DB into each worker's env; that wins.
    Otherwise: the back-compat `default` board is ~/.hermes/kanban.db; a named
    board lives at ~/.hermes/kanban/boards/<slug>/kanban.db.
    """
    env = os.environ.get("HERMES_KANBAN_DB")
    if env:
        return Path(env).resolve()
    if config.board == "default":
        return Path.home() / ".hermes" / "kanban.db"
    return Path.home() / ".hermes" / "kanban" / "boards" / config.board / "kanban.db"


def first_linked_task(fm: dict[str, Any]) -> str | None:
    tasks = fm.get("linked_kanban_tasks") or []
    if not tasks:
        return None
    first = tasks[0]
    return first.get("task_id") if isinstance(first, dict) else first


def append_note(body: str, note: str) -> str:
    return body.rstrip() + f"\n\n## {utc_now_iso()}\n\n{note}\n"


def require_status(fm: dict[str, Any], slug: str) -> None:
    actual = fm.get("status")
    if actual != EXPECTED_STATUS:
        die_state(f"Item {slug} is {actual!r}; expected {EXPECTED_STATUS!r}. Gate not active — refusing.")


# --------------------------------------------------------------------------- #
# actions
# --------------------------------------------------------------------------- #


def action_approve(slug: str) -> dict[str, Any]:
    config = load_config()
    vault = ItemVault(vault_dir(config))
    engine = TriageEngine(config, vault)

    item = vault.load(slug)
    fm, body = item.frontmatter, item.body
    require_status(fm, slug)

    path_name = fm.get("path")
    if path_name not in config.paths:
        die_state(f"Item {slug} has invalid `path`: {path_name!r}. Known: {sorted(config.paths)}.")
    triage_id = first_linked_task(fm)
    if not triage_id:
        die_state(f"Item {slug} has no `linked_kanban_tasks` root task.")

    specs = engine.fulfillment_specs(slug, path_name)
    if not specs:
        die_state(f"Path {path_name!r} has no `fulfill:` stages in triage.yaml — nothing to spawn.")

    # Ensure the shared persistent workspace exists before workers cwd into it.
    ws = engine.workspace_for(path_name, slug)
    ws.mkdir(parents=True, exist_ok=True)

    store = KanbanStore(board_db(config))
    conn = store.connect()
    created: list[dict[str, Any]] = []
    try:
        # First stage: `ready` now (no blocking parent — a child of the still-open
        # triage task would sit in `todo` forever). Each later stage parents to the
        # previous so the kernel promotes it exactly when its predecessor finishes.
        prev_id: str | None = None
        for spec in specs:
            task_id = store.create_task(
                conn,
                title=spec.title,
                body=spec.body,
                assignee=spec.assignee(config),
                parents=[prev_id] if prev_id else None,
                created_by="hermes-triage:human-action",
                workspace_kind=spec.workspace_kind,
                workspace_path=spec.workspace_path,
            )
            created.append({"task_id": task_id, "title": spec.title, "assignee": spec.assignee(config)})
            prev_id = task_id

        chain_desc = " → ".join(f"`{c['title']}`" for c in created)
        store.comment(conn, triage_id, author="human",
                      body=f"✅ Approved. Spawned {path_name} chain: {chain_desc} (first: `{created[0]['task_id']}`).")
        conn.commit()
    finally:
        conn.close()

    fm["status"] = "approved"
    fm["approved_at"] = utc_now_iso()
    fm.setdefault("linked_kanban_tasks", []).extend(c["task_id"] for c in created)
    item.body = append_note(body, f"✅ **Approved by human.** Spawned {path_name} chain: {chain_desc}.")
    vault.save(item)
    return {"ok": True, "action": "approve", "slug": slug, "path": path_name, "chain": created,
            "next_task_id": created[0]["task_id"], "next_assignee": created[0]["assignee"]}


def action_shelve(slug: str, reason: str | None) -> dict[str, Any]:
    config = load_config()
    vault = ItemVault(vault_dir(config))
    item = vault.load(slug)
    fm, body = item.frontmatter, item.body
    require_status(fm, slug)
    triage_id = first_linked_task(fm)

    store = KanbanStore(board_db(config))
    conn = store.connect()
    try:
        if triage_id:
            store.close_task(conn, triage_id, outcome="shelved_by_human",
                             summary=f"Shelved by human at gate. Reason: {reason or '(none given)'}")
            store.comment(conn, triage_id, author="human", body=f"🗑 Shelved.{f' Reason: {reason}' if reason else ''}")
        conn.commit()
    finally:
        conn.close()

    fm["status"] = "shelved_by_human"
    fm["shelved_at"] = utc_now_iso()
    if reason:
        fm["shelved_reason"] = reason
    item.body = append_note(body, "🗑 **Shelved by human at gate.**" + (f"\n\nReason: {reason}" if reason else ""))
    vault.save(item)
    return {"ok": True, "action": "shelve", "slug": slug, "reason": reason, "triage_task_closed": triage_id}


def action_shelve_all(reason: str | None, exceptions: set[str] | None = None) -> dict[str, Any]:
    """Shelve every item currently `awaiting_approval` — 'say no to the rest'."""
    config = load_config()
    vault = ItemVault(vault_dir(config))
    exceptions = exceptions or set()
    shelved: list[str] = []
    for path in sorted(vault.root.glob("*.md")):
        slug = path.stem
        if slug in exceptions:
            continue
        try:
            item = vault.load(slug)
        except (ValueError, FileNotFoundError):
            continue
        if item.frontmatter.get("status") != EXPECTED_STATUS:
            continue
        action_shelve(slug, reason)
        shelved.append(slug)
    return {"ok": True, "action": "shelve-all", "count": len(shelved), "shelved": shelved, "spared": sorted(exceptions)}


def action_modify(slug: str, change: str) -> dict[str, Any]:
    if not change.strip():
        die_input("--change cannot be empty.")
    config = load_config()
    vault = ItemVault(vault_dir(config))
    item = vault.load(slug)
    fm, body = item.frontmatter, item.body
    require_status(fm, slug)
    triage_id = first_linked_task(fm)
    if not triage_id:
        die_state(f"Item {slug} has no `linked_kanban_tasks` root task.")

    propose_role = config.get_path(fm.get("path", "")).propose_role if fm.get("path") in config.paths else "orchestrator"
    redraft_body = (
        f"Human requested modifications to the proposal for item `{slug}`.\n\n"
        f"Requested change:\n> {change}\n\n"
        "Redraft the proposal and re-send it to the human. After re-sending, set "
        "item status back to `awaiting_approval`.\n"
    )
    store = KanbanStore(board_db(config))
    conn = store.connect()
    try:
        # No blocking parent: the redraft must run now (created `ready`).
        redraft_id = store.create_task(
            conn, title=f"redraft_proposal: {slug}", body=redraft_body,
            assignee=config.role_to_profile(propose_role), created_by="hermes-triage:human-action",
        )
        store.comment(conn, triage_id, author="human", body=f"✏️ Modification requested: {change}\n\nRedraft task: `{redraft_id}`.")
        conn.commit()
    finally:
        conn.close()

    fm["status"] = "awaiting_redraft"
    fm["modify_requested_at"] = utc_now_iso()
    fm.setdefault("linked_kanban_tasks", []).append(redraft_id)
    item.body = append_note(body, f"✏️ **Human requested modification:**\n\n> {change}\n\nRedraft task: `{redraft_id}`")
    vault.save(item)
    return {"ok": True, "action": "modify", "slug": slug, "change": change, "redraft_task_id": redraft_id}


# --------------------------------------------------------------------------- #
# errors + CLI
# --------------------------------------------------------------------------- #


def die_input(msg: str) -> None:
    print(json.dumps({"ok": False, "error_kind": "input", "message": msg})); sys.exit(1)


def die_state(msg: str) -> None:
    print(json.dumps({"ok": False, "error_kind": "state", "message": msg})); sys.exit(2)


def die_backend(msg: str) -> None:
    print(json.dumps({"ok": False, "error_kind": "backend", "message": msg})); sys.exit(3)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="proposal_actions", description="Human-gate action handler (config-driven).")
    sub = parser.add_subparsers(dest="action", required=True)
    p_app = sub.add_parser("approve"); p_app.add_argument("slug")
    p_shl = sub.add_parser("shelve"); p_shl.add_argument("slug"); p_shl.add_argument("--reason", default=None)
    p_sha = sub.add_parser("shelve-all")
    p_sha.add_argument("--reason", default="bulk shelved by human")
    p_sha.add_argument("--except", dest="exceptions", action="append", default=[])
    p_mod = sub.add_parser("modify"); p_mod.add_argument("slug"); p_mod.add_argument("--change", required=True)
    args = parser.parse_args(argv)

    try:
        if args.action == "approve":
            result = action_approve(args.slug)
        elif args.action == "shelve":
            result = action_shelve(args.slug, args.reason)
        elif args.action == "shelve-all":
            result = action_shelve_all(args.reason, set(args.exceptions or []))
        elif args.action == "modify":
            result = action_modify(args.slug, args.change)
        else:
            die_input(f"Unknown action: {args.action!r}"); return
    except SystemExit:
        raise
    except (ValueError, FileNotFoundError) as exc:
        die_state(str(exc)); return
    except Exception as exc:
        die_backend(f"Unhandled error: {type(exc).__name__}: {exc}"); return
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
