"""Hermes Multi-Agent Workflow — generic detect → judge → route → gate → fulfill triage pipeline.

This package is DOMAIN-AGNOSTIC. Nothing in here should mention your specific
subject matter (bugs, pain points, leads, tickets, …). All domain specifics live
in `triage.yaml` and the template/skill files it points at.

If you are an AI agent adapting this template: read `AGENTS.md` at the repo root
first, then `docs/04-adapting-to-your-domain.md`. Do NOT edit this package to
encode your domain — edit `triage.yaml`. Touch the engine only to add a new
*mechanism*, never a new *topic*.
"""
