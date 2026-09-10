---
name: section-draft
description: >
  Mark the shell up into the section: the deal's facts, the book's analyses
  with their results, the letter's review list and assumptions, the proxy's
  defined terms, in the advisor's own language, scored against the package as
  it goes. Use when the user says "draft the section", "mark up the shell",
  "write the opinion section", or after the shell in the pipeline.
argument-hint: "[deal code] [--mode objective|procedure] [--model opus|fable]"
---

# /section-draft

1. Read the profile's drafting mode (default objective) and drafter model (default opus); `--mode` and `--model` in `$ARGUMENTS` win for this run. Read `${CLAUDE_PLUGIN_ROOT}/references/task-objective.md` or `task-procedure.md` accordingly; substitute the deal directory.
2. Draft through the `fairness-opinion-legal:section-drafter` agent: Agent tool with `model` set to the drafter model (`opus` or `fable`) and the prompt `stage: section-draft only; deal: <deal dir>; mode: <mode>`. Without an Agent tool, draft in this session and record its model. Either way the drafter writes `draft/section.txt` and `draft/log.md` following the task text, runs `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/selfscore.py <deal dir> draft/section.txt` as often as useful, and saves the last result to `draft/selfscore.json`.
3. Show the self-score summary, the drafter model, and the log's list of missing facts. Hand off to redline.

## The two modes

- **objective** (default): the task states the objective, the inputs and what is scored, nothing about how to work. The drafter is trusted to find the method; the self-scorer is the feedback.
- **procedure**: a ten-step procedure derived from the precedent bank and prior drafts, with a form note per advisor and a checklist. Same inputs, same scoring.

Both were run on the same 24 deals; see `references/scoring.md` for what is measured and the numbers to date.

## Rules that are not mode-dependent

- The section reads as filed text: no commentary, placeholders, drafting notes or markers in `section.txt`. Reviewer markers go in the log as `[REVIEWER: ...]` items with the paragraph they concern; if a marker must sit in the text because a sentence cannot be completed (a fee amount with no engagement letter), use exactly `[REVIEWER: fee amount]` so the redline stage can list them.
- A fact not in the inputs is omitted and logged, never invented; in particular never write "no prior relationships" without the relationship memo.
- Names: selected companies by full legal name; a precedent that was the sale of a business line described as the sale of that line; sponsors as this advisor's precedents treat them.
- Defined terms: once the proxy defines a term, the section uses it every time; with no glossary, introduce each term once in the advisor's form and list the introduced terms in the log.

## Log format

```
# <deal code> drafting log
Drafter: <opus | fable> (<objective | procedure> mode)
Base: <accession> (<target>, <date>) ; borrowed: <accession>: <analysis> ...
Analyses classified: ...
Deletions (paragraph, reason grounded in the book or the letter): ...
Facts not available and omitted: ...
Terms introduced without a glossary: ...
Self-score: <last summary line>
[REVIEWER: ...] items: ...
```

## What it does NOT do

- It does not deliver. The redline stage renders and the reviewer signs off.
