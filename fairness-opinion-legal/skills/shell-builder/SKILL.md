---
name: shell-builder
description: >
  Build the shell for the section: pick the base precedent among the approved
  set (regime, analyses, structure, length, recency) and splice in same-advisor
  paragraphs for any analysis the book has that the base lacks, with provenance
  and markers. Use when the user says "build the shell", "which precedent should
  we start from", or after precedent search in the pipeline.
argument-hint: "[deal code] [--base <accession>]"
---

# /shell-builder

First: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/feedback.py for <deal dir> --stage shell` prints the reviewer's notes from earlier runs that apply here; follow them.

1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build_shell.py <deal dir> [--base <accession>]`.
2. Show the rationale (three candidates, scores, the one selected) and the splice list. Stop at the shell gate only if the profile has it on.

## What the script writes

- `shell/rationale.json`: the three best bases with their scores. Score = Jaccard overlap of the book's valuation analyses with the precedent's, plus regime match, plus structure match (sum of the parts; stock against cash consideration), plus length fit, plus recency.
- `shell/shell_suggested.txt`: the base as filed.
- `shell/shell_composite.txt`: the base with every analysis paragraph tagged. `[[NOT IN THIS BOOK: ...]]` marks an analysis the base has and the book lacks (delete unless the book has it after all). `[[BORROWED FROM <accession>: ...]]` marks paragraphs spliced from another section by the same advisor for an analysis the base lacks.
- `shell/rationale.json` also lists `not_in_precedents` (analyses in the book that none of the precedents presents: the drafter omits them and logs them) and `reference_item_form` (how this advisor's precedents present reference-only items, quoted).
- `shell/shell_composite_eligible.txt`: the same with the not-in-book segments removed and markers stripped, for scoring.
- `shell/provenance.json`: every segment's source.

## Show

```
Base: ARC Document Solutions, 2024-10-16 (13e-3) — score 1.25; has comps, dcf, lbo, precedents, premiums
Alternatives: Science 37 2024 (1.01), SOC Telemed 2022 (0.99)
Spliced in: targets from SOC Telemed 2022; trading_range from Science 37 2024
Not in this book (marked for deletion): none
Shell length: 28,961 characters
```

A firm shell in `precedents/` competes on the same score; if it wins, say so.

## What it does NOT do

- It does not change the advisor's wording. The shell is the precedent text with markers; the markup stage changes facts.
- It does not splice paragraphs from another advisor.
