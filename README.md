# fairness-opinion-legal

A Claude plugin that drafts the "Opinion of [Financial Advisor]" section of a merger proxy statement the way a
transactional associate does it: find the advisor's own filed sections, pick the closest one, change only the deal facts,
and hand the reviewer a clean draft with a redline. Built from public EDGAR filings only. Every output is a draft for
attorney review, not legal advice.

> Companion to the write-up at [bsovocool16/fairness-opinions](https://github.com/bsovocool16/fairness-opinions) (private):
> the same method, tested across seven iterations on 24 held-out deals, with the scoring that drives it.

## What it does, in order

| stage | skill | what happens | gate |
|---|---|---|---|
| 0 | `cold-start-interview` | practice profile: who you are, the SEC contact identity, defaults, gates | once |
| 1 | `deal-intake` | asks the regime (Rule 13e-3 or conventional) first, then prompts for the board book, the opinion letter, the deal facts and the optional inputs; reads the book's analyses | confirm |
| 2 | `precedent-search` | finds the advisor's filed sections on EDGAR, verifies each, ranks by regime, coverage and recency | approve the set |
| 3 | `shell-builder` | picks the base section and splices in same-advisor paragraphs for analyses it lacks, with provenance | optional |
| 4 | `section-draft` | marks the shell up with the deal's facts, scores itself against the package, writes the log | |
| 5 | `redline` | clean draft plus a redline against the shell (and against any prior draft) | reviewer sign-off |

`pipeline` runs 1 to 5 in sequence, stopping at every gate the profile turns on. `proxy-glossary` is the optional step
between 1 and 4 when a draft proxy exists. `matter-workspace` keeps deals separate. `customize` edits the profile.

## Install

```bash
claude plugin marketplace add bsovocool16/fairness-opinion-legal   # or point at a local clone
claude plugin install fairness-opinion-legal
cd <plugin root>/scripts/redline && npm install                     # the docx renderer
```

Python 3.9+ with `requests` and `beautifulsoup4`; `pdftotext` for board books; LibreOffice for PDF output. Then run
`/fairness-opinion-legal:cold-start-interview`.

## Inputs, and what is not public

The method was learned from public filings: board books filed as exhibit (c) to Schedule 13E-3, opinion letters filed as
proxy annexes, and the sections as filed. Two inputs a drafter has in practice are not public and were never part of the
training: the engagement letter (fee and expense terms) and the advisor's relationship disclosure memo (prior and current
relationships with the parties). Intake asks for both as optional uploads; with them the fees-and-relationships paragraph is
drafted from the source rather than left for the reviewer.

## Layout

```
.claude-plugin/plugin.json   manifest
CLAUDE.md                    practice-profile template (the interview writes the live copy to ~/.claude/plugins/config/fairness-opinion-legal/)
skills/<name>/SKILL.md       one skill per stage
scripts/                     precedent search, book classifier, shell builder, self-scorer, glossary, text extraction
scripts/redline/             the Litera-style comparison tool (docx + pdf)
references/                  the drafting task texts, the scoring, and regime notes
agents/                      the named end-to-end agent
```

Copyright 2026 Benjamin Sovocool. Private repository.
