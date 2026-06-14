# Deliverable spec — VIDEO path

> Inlined into every `video`-path worker's task body. It pins the OUTPUT FORMAT
> so the agent produces something in your house style instead of generic output.
> **Replace the specifics below with your own style.** The more concrete this is,
> the less the agent drifts.

## What the path produces

1. `slides.html` — a self-contained slide deck (single file, web fonts only).
2. `script.md` — a speaker script that tracks the deck slide-for-slide.

Both written to the shared persistent workspace (`work/videos/<slug>/`).

## Slide style

<!-- TODO: describe YOUR deck aesthetic precisely, or point at a reference file. -->
- Self-contained HTML, no build step, no external assets except web fonts.
- <your color theme, font stack, layout conventions>
- Reference deck to match exactly: <path to an existing deck>. Read it first.
- One H1 title slide, then one slide per outline beat.

## Script format

<!-- TODO: describe YOUR script conventions. -->
- Per slide: an opening line + talking-point bullets + a line to land on.
- End matter: recording notes, a fact sheet (every cited number → source), and an
  assets checklist.
- The script reads `slides.html` as input so it matches the real deck.

## Quality bar

- Every factual claim traces to a source in the fact sheet.
- Don't pad runtime. A 4-minute topic is a 4-minute video.
- Match the reference voice and visual style; don't invent a new tone.
