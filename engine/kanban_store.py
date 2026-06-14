"""Thin writer over the Hermes Kanban SQLite board.

The Kanban board is the inter-agent bus. The engine creates tasks (cards) on it;
the Hermes gateway's dispatcher claims `ready` cards and spawns the assigned
agent. Parent links drive fan-in: a child task stays `todo` until every parent is
`done`, then the kernel auto-promotes it to `ready`.

This is generic Hermes plumbing — you should not need to edit it. The only
domain-ish constant is `created_by`, a free-text provenance tag.

NOTE: this writes the Hermes board schema directly. If a future Hermes release
changes the `tasks` columns, update the INSERT here. See `docs/02-the-board.md`.
"""
from __future__ import annotations

import json
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_epoch() -> int:
    return int(datetime.now(timezone.utc).timestamp())


class KanbanStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path.resolve()

    def connect(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise FileNotFoundError(f"Kanban DB not found: {self.db_path}")
        conn = sqlite3.connect(str(self.db_path), isolation_level="DEFERRED")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @staticmethod
    def new_task_id() -> str:
        return "t_" + secrets.token_hex(4)

    def create_task(
        self,
        conn: sqlite3.Connection,
        *,
        title: str,
        body: str,
        assignee: str,
        parents: list[str] | None = None,
        created_by: str = "hermes-multi-agent-workflow",
        workspace_kind: str = "scratch",
        workspace_path: str | None = None,
    ) -> str:
        task_id = self.new_task_id()
        now = utc_now_epoch()
        # No parents → `ready` (runs now). With parents → `todo` until they finish.
        status = "todo" if parents else "ready"
        conn.execute(
            """
            INSERT INTO tasks (
                id, title, body, assignee, status, priority,
                created_by, created_at, workspace_kind, workspace_path, consecutive_failures
            ) VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?, 0)
            """,
            (task_id, title, body, assignee, status, created_by, now, workspace_kind, workspace_path),
        )
        if parents:
            for parent in parents:
                conn.execute(
                    "INSERT OR IGNORE INTO task_links (parent_id, child_id) VALUES (?, ?)",
                    (parent, task_id),
                )
        self.append_event(conn, task_id, "created", {"assignee": assignee, "parents": parents or []})
        return task_id

    def comment(self, conn: sqlite3.Connection, task_id: str, *, author: str, body: str) -> None:
        conn.execute(
            "INSERT INTO task_comments (task_id, author, body, created_at) VALUES (?, ?, ?, ?)",
            (task_id, author, body, utc_now_epoch()),
        )
        self.append_event(conn, task_id, "comment_added", {"author": author})

    def close_task(self, conn: sqlite3.Connection, task_id: str, *, outcome: str, summary: str) -> None:
        now = utc_now_epoch()
        conn.execute("UPDATE tasks SET status = 'done', completed_at = ?, result = ? WHERE id = ?", (now, summary, task_id))
        self.append_event(conn, task_id, "done", {"outcome": outcome, "summary": summary})

    def append_event(self, conn: sqlite3.Connection, task_id: str, kind: str, payload: dict[str, Any] | None = None) -> None:
        conn.execute(
            "INSERT INTO task_events (task_id, kind, payload, created_at) VALUES (?, ?, ?, ?)",
            (task_id, kind, json.dumps(payload or {}), utc_now_epoch()),
        )
