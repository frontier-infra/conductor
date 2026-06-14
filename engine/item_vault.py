"""The item vault — one markdown file per tracked item.

An "item" is the generic unit the pipeline triages: a bug, a pain point, a lead,
a support ticket, a content idea — whatever your `triage.yaml` is about. Each
item is a markdown file with YAML frontmatter at `vault/items/<slug>.md`.

This is generic. The frontmatter fields below are the engine's required spine;
your domain can ADD fields freely (the writer preserves unknown keys). Do not
rename the spine fields — `scoring`, `routing`, and `proposal_actions` read them.

You should rarely need to edit this file when adapting the template.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .frontmatter import dumps_frontmatter, parse_frontmatter

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")


@dataclass
class Item:
    path: Path
    frontmatter: dict[str, Any]
    body: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ItemVault:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def item_path(self, slug: str) -> Path:
        if not SLUG_RE.match(slug):
            raise ValueError(f"Invalid slug: {slug!r}")
        path = (self.root / f"{slug}.md").resolve()
        if self.root not in path.parents:
            raise ValueError(f"Slug resolves outside vault: {slug!r}")
        return path

    def load(self, slug: str) -> Item:
        path = self.item_path(slug)
        if not path.exists():
            raise FileNotFoundError(path)
        fm, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        return Item(path=path, frontmatter=fm, body=body)

    def save(self, item: Item) -> None:
        item.path.parent.mkdir(parents=True, exist_ok=True)
        item.path.write_text(dumps_frontmatter(item.frontmatter, item.body), encoding="utf-8")

    def create_item(
        self,
        *,
        slug: str,
        title: str,
        sources: list[dict[str, Any]],
        body: str,
        embedding: list[float] | None = None,
    ) -> Item:
        path = self.item_path(slug)
        if path.exists():
            raise FileExistsError(path)
        # The engine's required spine. Add domain fields after creation if needed;
        # they are preserved on save. `path` here is the ROUTE decision (which
        # fulfillment path the router chose), not a filesystem path.
        fm: dict[str, Any] = {
            "slug": slug,
            "title": title,
            "first_seen": utc_now_iso(),
            "sources": sources,
            "score": None,
            "score_breakdown": {},
            "path": None,                 # set by the router: one of paths.* in triage.yaml
            "status": "triage",
            "embedding": embedding or [],
            "linked_kanban_tasks": [],
            "cost_spent_usd": 0.0,
        }
        item = Item(path=path, frontmatter=fm, body=body)
        self.save(item)
        return item

    def set_status(self, slug: str, status: str) -> Item:
        item = self.load(slug)
        item.frontmatter["status"] = status
        self.save(item)
        return item

    def append_note(self, slug: str, note: str) -> Item:
        item = self.load(slug)
        item.body = item.body.rstrip() + f"\n\n## {utc_now_iso()}\n\n{note}\n"
        self.save(item)
        return item

    def append_source(self, slug: str, source: dict[str, Any]) -> Item:
        item = self.load(slug)
        item.frontmatter.setdefault("sources", []).append(source)
        self.save(item)
        return item
