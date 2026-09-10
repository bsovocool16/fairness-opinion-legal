---
name: precedent-search
description: >
  Find the financial advisor's own filed opinion sections on EDGAR for a deal,
  verify each filing carries the section, read which analyses it presents, and
  rank by regime, coverage of the book's analyses and recency. Use when the user
  says "find precedents", "what has this bank filed", "pull the shell candidates",
  or after intake in the pipeline.
argument-hint: "[deal code] [--top N] [--years N]"
---

# /precedent-search

First: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/feedback.py for <deal dir> --stage search` prints the reviewer's notes from earlier runs that apply here; follow them.

1. Read the deal's `facts.json` (advisor, opinion date, regime) and `deck_analyses.json`.
2. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/search_deal.py <deal dir> [--top N] [--years N]`. It sends the SEC contact identity from the profile as the User-Agent and writes `precedents/<accession>.txt`, `precedents/INDEX.json` and prints the table.
3. Show the table and stop at the precedent gate if the profile has it on.

## How the search works, in one paragraph

Full-text search for the phrase "opinion of <advisor>" over DEFM14A, DEFM14C, SC 14D9 and SC 13E3 filings in the look-back window, filings before the deal's opinion date only. One sub-search per analysis narrows the candidates; the leading ones are fetched, the section is cut from the filing (or from the proxy exhibit of a Schedule 13E-3), and the analyses it presents are read from the text. Ranking: same regime first, then coverage of the book's analyses, then overlap, then recency. On the held-out test this recipe found 91% of a 479-section library across 17 advisors and every extra filing it returned was a real section.

## Table to show

```
#  filing date  target (form)                        regime        presents                              coverage
1  2024-10-16   ARC Document Solutions (DEFM14A)     13e-3         comps, dcf, lbo, precedents, premiums   0.71
2  2022-03-07   SOC Telemed (DEFM14A)                conventional  comps, dcf, lbo, precedents, premiums   0.71
...
firm shells in precedents/: <list or none>
```

Then: "Approve this set, or tell me which to drop or add (an accession number, a filing URL, or a file)." Adding a URL: fetch it, cut the section with the same script (`--add <url or accession>`). Firm shells from intake are listed alongside.

## Degraded cases

- Fewer than three verified sections in the window: widen to nine years and say so; the profile's window is a default, not a rule.
- Advisor with no filed sections (a boutique's first public deal): report it, and offer to search a comparable advisor's sections only as a form reference, clearly labeled; the draft then carries a marker that the language is not this advisor's.
- EDGAR rate limit or outage: the script retries with backoff; if it fails, say so and stop. Never substitute memory for a filing.

## Handoff

```yaml
handoff:
  next: shell-builder
  precedents: precedents/INDEX.json   # approved set, with accession, date, form, regime, presented analyses, coverage
```

## What it does NOT do

- It does not read the deal's own filing, if one exists; the cut-off date excludes it.
- It does not rank by the firm's preferences unless a firm shell was supplied.
