"""Core engine tests — run with:  python -m unittest discover -s tests

These cover the GENERIC engine against a synthetic config, proving the pipeline
logic is config-driven (not hardcoded to any domain). When you adapt the
template, keep these green and add domain cases.

Requires PyYAML (engine.config imports it). See requirements.txt.
"""
from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.config import ConfigError, TriageConfig  # noqa: E402
from engine.engine import TriageEngine  # noqa: E402
from engine.routing import route_from_classification  # noqa: E402
from engine.scoring import score_from_breakdown  # noqa: E402


def make_config(**overrides) -> TriageConfig:
    """A minimal but complete synthetic config — the engine's general shape."""
    data = {
        "name": "test-pipeline",
        "board": "test-board",
        "workspace_root": "./work",
        "cost_gate_usd": 5,
        "sources": [{"id": "s1", "profile": "scout1", "skill": "scout-skill", "schedule": "0 * * * *", "query": "find things"}],
        "item_schema": {"fields": ["title", "claim", "sources"]},
        "dedup": {"method": "token-cosine", "duplicate_threshold": 0.62, "possible_threshold": 0.40},
        "rubric": {
            "threshold": 50,
            "dimensions": [
                {"key": "frequency", "max": 25, "hint": "h"},
                {"key": "intensity", "max": 25, "hint": "h"},
            ],
        },
        "research_lanes": {"role": "researcher", "lanes": ["verify", "audit"], "classifier_lane": "audit"},
        "route": {"classifier": "audit.quality", "map": {"missing": "build", "good": "shelve"}},
        "paths": {
            "build": {
                "prep": [{"stage": "synth", "role": "analyst"}],
                "propose": {"role": "orchestrator"},
                "fulfill": [{"stage": "do_build", "role": "builder"}, {"stage": "report", "role": "orchestrator"}],
                "workspace_subdir": "builds",
            },
            "shelve": {"auto": True},
        },
        "roles": {"orchestrator": "orchestrator", "researcher": "researcher", "analyst": "analyst", "builder": "builder"},
        "gate": {"channel": "telegram", "approve": ["approve"], "shelve": ["shelve"], "modify": ["modify"]},
    }
    data.update(overrides)
    return TriageConfig.from_dict(data)


class TestConfig(unittest.TestCase):
    def test_loads_and_validates(self):
        cfg = make_config()
        self.assertEqual(cfg.name, "test-pipeline")
        self.assertEqual(cfg.rubric.max_total, 50)
        self.assertEqual(cfg.role_to_profile("builder"), "builder")

    def test_route_target_must_exist(self):
        with self.assertRaises(ConfigError):
            make_config(route={"classifier": "audit.quality", "map": {"missing": "nonexistent_path"}})

    def test_undefined_role_rejected(self):
        bad_paths = {
            "build": {"fulfill": [{"stage": "x", "role": "ghost"}]},
            "shelve": {"auto": True},
        }
        with self.assertRaises(ConfigError):
            make_config(paths=bad_paths)

    def test_unreachable_threshold_rejected(self):
        with self.assertRaises(ConfigError):
            make_config(rubric={"threshold": 999, "dimensions": [{"key": "a", "max": 10}]})


class TestScoring(unittest.TestCase):
    def test_breakdown_applies_threshold(self):
        cfg = make_config()
        r = score_from_breakdown({"frequency": 25, "intensity": 25}, cfg.rubric)
        self.assertEqual(r.total, 50)
        self.assertTrue(r.advance)

    def test_below_threshold_does_not_advance(self):
        cfg = make_config()
        r = score_from_breakdown({"frequency": 10, "intensity": 10}, cfg.rubric)
        self.assertFalse(r.advance)

    def test_clamps_and_ignores_unknown(self):
        cfg = make_config()
        r = score_from_breakdown({"frequency": 999, "bogus": 5}, cfg.rubric)
        self.assertEqual(r.breakdown["frequency"], 25)  # clamped to max
        self.assertTrue(any("bogus" in n for n in r.notes))


class TestRouting(unittest.TestCase):
    def test_maps_value_to_path(self):
        cfg = make_config()
        self.assertEqual(route_from_classification("missing", cfg.route), "build")
        self.assertEqual(route_from_classification("GOOD", cfg.route), "shelve")  # case-insensitive

    def test_unknown_classification_raises(self):
        cfg = make_config()
        with self.assertRaises(ValueError):
            route_from_classification("weird", cfg.route)


class TestEngineSpecs(unittest.TestCase):
    def test_research_specs_parallel_under_triage(self):
        engine = TriageEngine(make_config())
        specs = engine.research_specs("my-slug", "t_root")
        self.assertEqual(len(specs), 2)
        for s in specs:
            self.assertEqual(s.parents, ["t_root"])  # all parented to triage → run in parallel
        self.assertTrue(any("CLASSIFIER" in s.body for s in specs))  # classifier lane flagged

    def test_fulfillment_specs_persistent_workspace(self):
        engine = TriageEngine(make_config())
        specs = engine.fulfillment_specs("my-slug", "build")
        self.assertEqual([s.title for s in specs], ["do_build: my-slug", "report: my-slug"])
        for s in specs:
            self.assertEqual(s.workspace_kind, "dir")          # persistent, not scratch
            self.assertIn("builds", s.workspace_path)          # uses configured subdir
            self.assertIn("my-slug", s.workspace_path)

    def test_roles_resolve_to_profiles(self):
        cfg = make_config()
        engine = TriageEngine(cfg)
        specs = engine.fulfillment_specs("s", "build")
        self.assertEqual(specs[0].assignee(cfg), "builder")
        self.assertEqual(specs[1].assignee(cfg), "orchestrator")


if __name__ == "__main__":
    unittest.main()
