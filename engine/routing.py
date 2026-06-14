"""Routing — map a classification to a fulfillment path.

After the research fan-out, one lane (the `classifier_lane`) emits a
classification value. The router maps that value to a path defined under
`paths:` in triage.yaml.

This is fully config-driven: the map lives in `triage.yaml` (`route.map`), not in
code. To change routing behaviour, edit the YAML — not this file.
"""
from __future__ import annotations

from .config import Route


def route_from_classification(classification: str, route: Route) -> str:
    """Return the path name for a classification value.

    Raises ValueError on an unknown value so a misconfigured/misbehaving
    classifier fails loudly instead of silently dropping items.
    """
    key = (classification or "").strip().lower()
    normalized = {k.strip().lower(): v for k, v in route.map.items()}
    if key not in normalized:
        raise ValueError(
            f"Unknown classification {classification!r}. "
            f"Add it to route.map in triage.yaml. Known: {sorted(normalized)}."
        )
    return normalized[key]
