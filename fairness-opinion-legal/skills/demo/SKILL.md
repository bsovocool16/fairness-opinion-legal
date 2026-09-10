---
name: demo
description: >
  Show the whole path end to end on the bundled public deal (Distribution
  Solutions Group 2026, William Blair, Rule 13e-3): by default a replay of a
  completed run, stage by stage, from the uploads to the draft's redline against
  the section as filed; with --live, the real chain on the same board book (OCR,
  EDGAR search, shell, draft, redline). Use when the user says "demo", "show me
  how it works", "walk me through it", "end to end", or wants to see the tool
  before setting anything up. Needs no profile in replay mode.
argument-hint: "[--live] [--model opus|fable] [--stage intake|search|shell|draft|redline|filed]"
---

# /demo

## Replay (default)

1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/demo.py walk` (add `--stage <name>` when `$ARGUMENTS` names one). It prints one block per stage from the completed run in `${CLAUDE_PLUGIN_ROOT}/examples/distribution-solutions-2026/run/` and writes nothing.
2. Present the stages in order, each as its own short section: one or two sentences on what the stage does and what to notice, then the block as printed, tables intact. Never paraphrase or round the numbers. Give the paths of the files a stage produced; if a file-sending tool is available, send `redline/section.docx`, `redline/redline_vs_shell.pdf` and `filed/redline_vs_filed.pdf`.
3. Close with the two things a replay cannot show: the gates, where the pipeline stops for the attorney (after intake, after the precedent set, before delivery), and what a real deal needs (the profile with the SEC contact identity, the user's own book and letter, optionally the draft proxy, engagement letter and relationship memo). Mention that a correction given at any gate is saved by `feedback` and applied to later deals. Offer `--live`.

What to notice, per stage:
- Intake asks the regime first; a Rule 13e-3 deal and a conventional one get different precedents and different shells. The book was slide images; OCR read them.
- Search is live EDGAR: every candidate is fetched and verified to carry the advisor's own section before it is ranked.
- Shell: the base is chosen by analyses covered, regime, structure and recency, and every segment carries its source.
- Draft: advisor-language share, every analysis the advisor's precedents present carried with its results and none the advisor never files, selected companies by full legal name, every number traceable to an input, no commentary or placeholders.
- Redline against the shell is the reviewer's view of everything the drafter changed.
- Against the filing: the drafter never saw it; the remaining differences are mostly the proxy's defined terms, which `proxy-glossary` supplies when a draft proxy exists.

## Live (`--live`)

Say up front what it does: EDGAR requests under the user's SEC contact identity, OCR of 32 slides, one drafting pass on Opus (or Fable with `--model fable`), about ten minutes and a few hundred thousand tokens, writing only under the deals folder. Then:

1. Profile: if `~/.claude/plugins/config/fairness-opinion-legal/CLAUDE.md` is missing or its SEC contact is a placeholder, ask only for a name and e-mail and export `EDGAR_UA="Name email"` for this run; do not write the profile unless asked.
2. `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/demo.py setup-live <deals folder> [--code demo-dsgr-2026] [--model opus|fable]`: a fresh deal folder with the book, the letter and `facts.json` (the intake answers from the example), so intake's questions are already answered. The deals folder is the profile's, else `~/.claude/plugins/config/fairness-opinion-legal/deals/`.
3. Read the book as `deal-intake` does from its extraction step: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_text.py inputs/book.pdf inputs/book.txt --ocr` (report pages and OCR time), then `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/classify_book.py <deal folder>`, which writes `deck_analyses.json`. Show the analyses table: that is the intake gate, narrated rather than stopped at.
4. `precedent-search`, `shell-builder`, `section-draft` (drafter model from `--model`, else the profile, default opus), `redline`: follow each skill as written. Narrate each gate with its status line; stop only if the user asks to.
5. `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/demo.py filed <deal folder>`: the draft's redline against the section as filed, with the same numbers the replay shows for comparison.
6. Leave the folder in place and say its code, so `matter-workspace` can list or close it.

## What it does NOT do

- It does not touch any other deal folder, and it does not write the profile.
- The replay is not a live search: its precedents were fetched on September 9, 2026. `--live` fetches again, so the set can differ.
- It does not send anything anywhere.
