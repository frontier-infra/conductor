"""Item deduplication.

Two items can describe the same underlying thing in different words. Before the
engine spends money researching a candidate, it checks whether a similar item
already exists in the vault.

This module ships a deterministic, dependency-free **token-cosine** fallback so
the template runs and is unit-testable with no network call. For production you
will usually want **embedding-based** dedup: populate each item's `embedding`
frontmatter field from a real provider and switch `similar_items` to
cosine-over-embeddings. The classification thresholds and the three-way contract
(`duplicate` / `possible` / `new`) stay identical, so nothing downstream changes.

Thresholds come from `triage.yaml` (`dedup:` block) — pass them in, or use the
module defaults which match the reference config.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from .item_vault import ItemVault

# Defaults match triage.yaml's `dedup:` block. The token-cosine fallback runs
# COLDER than embedding cosine for differently-worded-but-same-topic text, hence
# the lower cutoffs. If you switch to embeddings, raise these (≈0.85 / 0.65).
DUPLICATE_THRESHOLD = 0.62
POSSIBLE_THRESHOLD = 0.40

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    """a an the of to in on for with and or but is are was were be been being it
    this that these those i you he she they we my your our their as at by from
    into out up down over under again then once here there all any both each few
    more most other some such no nor not only own same so than too very can will
    just don should now about which who whom what when where why how""".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS and len(t) > 1]


def _vector(text: str) -> Counter[str]:
    return Counter(tokenize(text))


def cosine(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    if not common:
        return 0.0
    dot = sum(a[t] * b[t] for t in common)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def text_similarity(left: str, right: str) -> float:
    return cosine(_vector(left), _vector(right))


def classify(score: float, duplicate_threshold: float = DUPLICATE_THRESHOLD, possible_threshold: float = POSSIBLE_THRESHOLD) -> str:
    """Map a similarity score to the three-way dedup decision."""
    if score >= duplicate_threshold:
        return "duplicate"
    if score >= possible_threshold:
        return "possible"
    return "new"


@dataclass
class Match:
    slug: str
    score: float
    decision: str


def _item_text(frontmatter: dict, body: str) -> str:
    parts = [str(frontmatter.get("title", "")), body]
    return "\n".join(p for p in parts if p)


def similar_items(
    candidate_text: str,
    vault: ItemVault,
    top_k: int = 3,
    duplicate_threshold: float = DUPLICATE_THRESHOLD,
    possible_threshold: float = POSSIBLE_THRESHOLD,
) -> list[Match]:
    """Rank existing vault items by similarity to `candidate_text`.

    Returns up to `top_k` matches sorted by descending score, each carrying the
    three-way decision (`duplicate` / `possible` / `new`).
    """
    cand = _vector(candidate_text)
    scored: list[Match] = []
    for path in sorted(vault.root.glob("*.md")):
        slug = path.stem
        try:
            item = vault.load(slug)
        except (ValueError, FileNotFoundError):
            continue
        score = cosine(cand, _vector(_item_text(item.frontmatter, item.body)))
        scored.append(Match(slug=slug, score=round(score, 4), decision=classify(score, duplicate_threshold, possible_threshold)))
    scored.sort(key=lambda m: m.score, reverse=True)
    return scored[:top_k]


def best_match(candidate_text: str, vault: ItemVault) -> Match | None:
    matches = similar_items(candidate_text, vault, top_k=1)
    return matches[0] if matches else None
