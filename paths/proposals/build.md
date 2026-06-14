# BUILD proposal template

> The orchestrator fills this in and sends it to the human at the gate. Keep it
> skimmable on a phone — the human approves from this alone. Adapt the fields to
> your domain. Reply verbs come from `gate:` in triage.yaml (no leading slash).

```
🔧 BUILD proposal: <title>   (slug: <slug>)

Problem
<one-paragraph synthesis of the item>

Sources
- <link>
- <link>

Why build
- Score: <total>/100 (<short breakdown>)
- Existing solutions: <none | broken — detail>
- Scope: <CLI tool | skill | playbook | …>  (must fit paths/rails/build.md)

Proposed solution
<the chosen candidate, 1–2 paragraphs>

Estimate
- Spend for build+test: ~$<X>
- Agent wall-clock: ~<N>

Reply:  approve <slug>   |   shelve <slug>: <reason>   |   modify <slug>: <change>
```
