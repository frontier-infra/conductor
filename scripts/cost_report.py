#!/usr/bin/env python3
"""Per-item LLM-spend report for the cost gate.

Walks the triage board for the tasks linked to an item and sums their cost
telemetry. Used to enforce `cost_gate_usd` from triage.yaml:
  - over budget BEFORE the gate → orchestrator pauses + notifies
  - over budget AFTER approval  → orchestrator notifies + continues

Usage:
  python scripts/cost_report.py <slug> [--gate 5]   # exits non-zero if over --gate

Degrades gracefully: if your Hermes build doesn't expose cost telemetry on the
board, it reports "telemetry unavailable" rather than guessing. This is a
TEMPLATE — the exact telemetry column/table depends on your Hermes version, so
the SQL below is marked where you may need to adjust it.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from engine.config import TriageConfig
from engine.item_vault import ItemVault
from proposal_actions import board_db, vault_dir  # reuse the same resolution


def linked_task_ids(slug: str, config: TriageConfig) -> list[str]:
    vault = ItemVault(vault_dir(config))
    fm = vault.load(slug).frontmatter
    ids = []
    for t in fm.get("linked_kanban_tasks") or []:
        ids.append(t.get("task_id") if isinstance(t, dict) else t)
    return [t for t in ids if t]


def sum_cost(db: Path, task_ids: list[str]) -> float | None:
    if not task_ids or not db.exists():
        return None
    conn = sqlite3.connect(str(db))
    try:
        # TODO: adjust to your Hermes telemetry schema. Common shapes:
        #   tasks.cost_usd, or a task_runs/usage table with a cost column.
        # We probe for a `cost_usd` column on tasks; absent → telemetry unavailable.
        cols = {r[1] for r in conn.execute("PRAGMA table_info(tasks)")}
        if "cost_usd" not in cols:
            return None
        marks = ",".join("?" * len(task_ids))
        row = conn.execute(
            f"SELECT COALESCE(SUM(cost_usd), 0) FROM tasks WHERE id IN ({marks})", task_ids
        ).fetchone()
        return float(row[0]) if row else 0.0
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Per-item spend report.")
    parser.add_argument("slug")
    parser.add_argument("--gate", type=float, default=None, help="USD budget; non-zero exit if exceeded.")
    parser.add_argument("--config", default="triage.yaml")
    args = parser.parse_args(argv)

    config = TriageConfig.load(args.config)
    gate = args.gate if args.gate is not None else config.cost_gate_usd
    ids = linked_task_ids(args.slug, config)
    total = sum_cost(board_db(config), ids)

    if total is None:
        print(json.dumps({"slug": args.slug, "cost_usd": None, "note": "telemetry unavailable", "tasks": len(ids)}))
        return 0
    over = total > gate
    print(json.dumps({"slug": args.slug, "cost_usd": round(total, 4), "gate_usd": gate, "over_budget": over, "tasks": len(ids)}, indent=2))
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())
