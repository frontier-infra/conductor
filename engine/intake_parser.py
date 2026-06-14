"""Parse a scout's intake report into structured candidates.

A scout (see `skills/templates/triage-scout/SKILL.md`) writes a markdown report
to `vault/intake/<ts>-<source>.md`. This parser turns that report into
`Candidate` objects the orchestrator can dedup and score.

The report FORMAT is a contract between the scout skill and this parser. The
default format below is simple and LLM-friendly:

    @optional-mention
    some_metadata_key: value

    ## Candidate: <title>
    Claim: <one-line claim>
    Sources:
      - url: https://...
        quote: "verbatim quote"
    Why it may matter: <one line>

If you change the fields a scout emits (see `item_schema` in triage.yaml), keep
this parser and the scout skill in sync. The three fields the rest of the engine
relies on are `title`, `claim`, and `sources`.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Candidate:
    title: str
    claim: str = ""
    sources: list[dict[str, str]] = field(default_factory=list)
    why_it_may_matter: str = ""


@dataclass
class IntakeReport:
    mention: str | None
    metadata: dict[str, str]
    candidates: list[Candidate]


def parse_intake_report(text: str) -> IntakeReport:
    lines = text.splitlines()
    mention = None
    metadata: dict[str, str] = {}
    candidates: list[Candidate] = []
    current: Candidate | None = None
    in_sources = False
    current_source: dict[str, str] | None = None

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("@") and mention is None:
            mention = stripped.split()[0]
            continue
        if stripped.startswith("## Candidate:"):
            if current_source is not None and current is not None:
                current.sources.append(current_source)
                current_source = None
            current = Candidate(title=stripped.split(":", 1)[1].strip())
            candidates.append(current)
            in_sources = False
            continue
        if current is None:
            if ":" in stripped and not stripped.startswith("#"):
                k, v = stripped.split(":", 1)
                metadata[k.strip()] = v.strip()
            continue
        if stripped.startswith("Claim:"):
            current.claim = stripped.split(":", 1)[1].strip()
            in_sources = False
        elif stripped == "Sources:":
            in_sources = True
        elif stripped.startswith("Why it may matter:"):
            if current_source is not None:
                current.sources.append(current_source)
                current_source = None
            current.why_it_may_matter = stripped.split(":", 1)[1].strip()
            in_sources = False
        elif in_sources and stripped.startswith("- "):
            if current_source is not None:
                current.sources.append(current_source)
            current_source = {}
            rest = stripped[2:].strip()
            if ":" in rest:
                k, v = rest.split(":", 1)
                current_source[k.strip()] = v.strip().strip('"')
        elif in_sources and current_source is not None and ":" in stripped:
            k, v = stripped.split(":", 1)
            current_source[k.strip()] = v.strip().strip('"')

    if current_source is not None and current is not None:
        current.sources.append(current_source)
    return IntakeReport(mention=mention, metadata=metadata, candidates=candidates)
