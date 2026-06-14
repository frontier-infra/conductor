"""Load and validate `triage.yaml` — the single file that defines a pipeline.

THIS is the generalization. The engine code is generic; `triage.yaml` is your
domain. Everything domain-specific — what you detect, how you score it, where it
routes, what each path produces — is data here, not code.

Adapting the template = editing `triage.yaml` (and the markdown templates it
points at). You should not need to edit the engine to change your subject matter.

Reads YAML via PyYAML. That's the engine's one third-party dependency; if it is
missing this module raises a clear, actionable error. (Item *files* still use the
stdlib frontmatter reader — only this config loader needs PyYAML.)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError as exc:  # pragma: no cover - environment guard
    raise ImportError(
        "triage.yaml is YAML; the config loader needs PyYAML.\n"
        "Install it:  pip install pyyaml\n"
        "(Only the config loader needs it — item files use the stdlib reader.)"
    ) from exc


class ConfigError(ValueError):
    """Raised with a human/agent-readable message when triage.yaml is invalid."""


# --------------------------------------------------------------------------- #
# Typed view over the config. Each dataclass mirrors a block in triage.yaml.
# Keep field names == YAML keys so docs/03-config-reference.md stays 1:1.
# --------------------------------------------------------------------------- #


@dataclass
class Source:
    id: str
    profile: str          # the Hermes profile this scout runs under
    skill: str            # the scout skill name installed on that profile
    schedule: str         # cron expression (registered in the gateway profile's store)
    query: str            # what the scout searches for (the domain prompt)


@dataclass
class RubricDimension:
    key: str
    max: int
    hint: str = ""        # guidance the orchestrator uses when scoring this dimension


@dataclass
class Rubric:
    threshold: int
    dimensions: list[RubricDimension]

    @property
    def max_total(self) -> int:
        return sum(d.max for d in self.dimensions)


@dataclass
class Stage:
    stage: str            # task title prefix, e.g. "prototype_build"
    role: str             # abstract role; mapped to a profile via `roles:`


@dataclass
class PathDef:
    name: str
    prep: list[Stage] = field(default_factory=list)       # runs BEFORE the human gate
    fulfill: list[Stage] = field(default_factory=list)    # runs AFTER approval
    propose_role: str = "orchestrator"                    # who drafts + sends the proposal
    proposal_template: str | None = None                  # markdown file under paths/
    workspace_subdir: str = ""                            # persistent dir bucket, e.g. "builds"
    scope_rails: str | None = None                        # hard-constraints md injected into workers
    deliverable_spec: str | None = None                   # output-format md injected into workers
    auto: bool = False                                    # True = terminal path (e.g. shelve), no work


@dataclass
class ResearchLanes:
    profile_role: str                # role the lanes run under (usually "researcher")
    lanes: list[str]                 # parallel lane task titles; all must finish before route
    classifier_lane: str             # the lane whose output the router reads


@dataclass
class Route:
    classifier: str                  # dotted path into research output, e.g. "<lane>.solution_quality"
    map: dict[str, str]              # classification value -> path name


@dataclass
class Dedup:
    method: str = "token-cosine"     # or "embedding"
    duplicate_threshold: float = 0.62
    possible_threshold: float = 0.40


@dataclass
class Gate:
    channel: str = "telegram"
    approve: list[str] = field(default_factory=lambda: ["approve"])
    shelve: list[str] = field(default_factory=lambda: ["shelve", "reject the rest"])
    modify: list[str] = field(default_factory=lambda: ["modify"])


@dataclass
class TriageConfig:
    name: str
    board: str
    workspace_root: str
    cost_gate_usd: float
    sources: list[Source]
    item_schema: list[str]
    dedup: Dedup
    rubric: Rubric
    research: ResearchLanes
    route: Route
    paths: dict[str, PathDef]
    roles: dict[str, str]
    gate: Gate
    raw: dict[str, Any] = field(default_factory=dict)

    # ----- convenience lookups the engine and proposal_actions use ----- #

    def role_to_profile(self, role: str) -> str:
        if role not in self.roles:
            raise ConfigError(
                f"Role {role!r} is used in a path/stage but is not defined in `roles:`. "
                f"Known roles: {sorted(self.roles)}."
            )
        return self.roles[role]

    def get_path(self, name: str) -> PathDef:
        if name not in self.paths:
            raise ConfigError(f"Path {name!r} is referenced but not defined under `paths:`.")
        return self.paths[name]

    @classmethod
    def load(cls, path: str | Path = "triage.yaml") -> "TriageConfig":
        p = Path(path)
        if not p.exists():
            raise ConfigError(f"Config not found: {p}. Copy and edit the example triage.yaml.")
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TriageConfig":
        def req(key: str) -> Any:
            if key not in data:
                raise ConfigError(f"triage.yaml is missing required top-level key: `{key}`.")
            return data[key]

        rubric_d = req("rubric")
        rubric = Rubric(
            threshold=int(rubric_d["threshold"]),
            dimensions=[RubricDimension(**d) for d in rubric_d["dimensions"]],
        )
        research_d = req("research_lanes")
        research = ResearchLanes(
            profile_role=research_d.get("role", "researcher"),
            lanes=list(research_d["lanes"]),
            classifier_lane=research_d.get("classifier_lane", research_d["lanes"][-1]),
        )
        route_d = req("route")
        route = Route(classifier=route_d["classifier"], map=dict(route_d["map"]))

        paths: dict[str, PathDef] = {}
        for name, pd in req("paths").items():
            pd = pd or {}
            paths[name] = PathDef(
                name=name,
                prep=[Stage(**s) for s in pd.get("prep", [])],
                fulfill=[Stage(**s) for s in pd.get("fulfill", [])],
                propose_role=(pd.get("propose") or {}).get("role", "orchestrator"),
                proposal_template=(pd.get("propose") or {}).get("template"),
                workspace_subdir=pd.get("workspace_subdir", name),
                scope_rails=pd.get("scope_rails"),
                deliverable_spec=pd.get("deliverable_spec"),
                auto=bool(pd.get("auto", False)),
            )

        cfg = cls(
            name=req("name"),
            board=req("board"),
            workspace_root=data.get("workspace_root", "./work"),
            cost_gate_usd=float(data.get("cost_gate_usd", 5)),
            sources=[Source(**s) for s in data.get("sources", [])],
            item_schema=list((data.get("item_schema") or {}).get("fields", [])),
            dedup=Dedup(**(data.get("dedup") or {})),
            rubric=rubric,
            research=research,
            route=route,
            paths=paths,
            roles=dict(req("roles")),
            gate=Gate(**(data.get("gate") or {})),
            raw=data,
        )
        cfg.validate()
        return cfg

    def validate(self) -> None:
        """Fail loudly with actionable messages. Called by the CLI `validate`."""
        errors: list[str] = []

        # Every route target must be a defined path.
        for value, target in self.route.map.items():
            if target not in self.paths:
                errors.append(f"route.map[{value!r}] -> {target!r}, but no such path under `paths:`.")

        # Every role used in any stage must be defined.
        used_roles = {self.research.profile_role}
        for p in self.paths.values():
            used_roles.add(p.propose_role)
            used_roles.update(s.role for s in p.prep + p.fulfill)
        for role in used_roles:
            if role not in self.roles:
                errors.append(f"Role {role!r} used by a path but missing from `roles:`.")

        # Rubric sanity.
        if self.rubric.threshold > self.rubric.max_total:
            errors.append(
                f"rubric.threshold ({self.rubric.threshold}) exceeds the sum of dimension maxes "
                f"({self.rubric.max_total}); nothing could ever pass."
            )

        # Classifier lane must exist.
        if self.research.classifier_lane not in self.research.lanes:
            errors.append(
                f"research_lanes.classifier_lane ({self.research.classifier_lane!r}) "
                f"is not one of the declared lanes {self.research.lanes}."
            )

        if errors:
            raise ConfigError("Invalid triage.yaml:\n  - " + "\n  - ".join(errors))
