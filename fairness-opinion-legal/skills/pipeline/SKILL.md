---
name: pipeline
description: >
  Run the whole chain for a deal: intake (regime first, then the uploads),
  precedent search on EDGAR, shell, markup, clean draft and redline, stopping at
  every gate the profile turns on. Use when the user says "draft the opinion
  section", "run the pipeline", "start from the deck", or hands over a board book
  and wants the section back.
argument-hint: "[deal code]"
---

# /pipeline

1. Profile check: if `~/.claude/plugins/config/fairness-opinion-legal/CLAUDE.md` is missing or has `[PLACEHOLDER]` markers, run `/fairness-opinion-legal:cold-start-interview` first.
2. Deal: `$ARGUMENTS` or the active deal, else `/fairness-opinion-legal:matter-workspace new`.
3. Stages, in order, each one its own skill; read that skill and follow it:
   - `deal-intake` → gate: confirm regime, facts, analyses
   - `proxy-glossary` if a draft proxy was supplied
   - `precedent-search` → gate: approve the set
   - `shell-builder` → gate only if the profile turns it on
   - `section-draft`
   - `redline` → gate: reviewer sign-off
4. After each stage append one line to `history.md` and show a one-line status. On a gate, stop and wait; do not continue on silence.

## Status line

```
[intake ✓] [glossary –] [search ✓ 8 precedents] [shell ✓ base ARC 2024] [draft ✓ self-score 0.61 / terms 12 / names 7/7] [redline ✓]
```

## When a stage cannot complete

Say which input or tool is missing and what the next stage would lose; offer the degraded path named in that stage's skill. Never skip a gate to keep moving.

## What it does NOT do

- It does not file, send, or share anything. Outputs stay in the deal folder until the reviewer signs off.
