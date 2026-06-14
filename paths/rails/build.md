# BUILD scope rails (HARD limits)

> This file is inlined into every `build`-path worker's task body by the engine.
> It is the safety boundary on what an autonomous agent is allowed to build.
> **Adapt it to your domain and your risk tolerance.** Keep it tight — vague
> rails are the difference between a useful prototype and an agent wandering off
> to build a SaaS app.

## Acceptable build targets

<!-- TODO: replace with the concrete, bounded artifacts YOUR pipeline may build. -->
- A Hermes skill (`SKILL.md` + optional tools)
- A Hermes plugin (dashboard plugin with API routes + frontend)
- A CLI tool (single script or single binary)
- A markdown playbook or template
- A small script (< 500 lines)
- A cron job + a single skill

## Never acceptable

<!-- TODO: your hard "no" list. Be specific; this is the guardrail. -->
- Full SaaS apps
- Stateful auth flows (accounts, OAuth, sessions)
- Anything requiring API keys not already provisioned in the profile's `.env`
- Anything needing real UI work beyond a dashboard plugin
- Anything that exfiltrates data or calls out to un-vetted services

## If a proposal doesn't fit the rails

Shelve it and say why, OR consider whether a different path applies (e.g. an
existing-but-confusing solution → the `video` path). **Do not expand the rails to
fit a proposal.** The rails are the contract.
