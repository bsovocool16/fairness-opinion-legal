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
| – | `demo` | replays a completed run on the bundled public deal stage by stage, through to a comparison with the section as filed; `--live` runs the chain for real on the same inputs | |

`pipeline` runs 1 to 5 in sequence, stopping at every gate the profile turns on. The drafter runs on Opus by default; `--model fable` on `pipeline`, `section-draft` or `demo --live`, or `Drafter model: fable` in the profile, switches it. `proxy-glossary` is the optional step
between 1 and 4 when a draft proxy exists. `matter-workspace` keeps deals separate. `customize` edits the profile.

## Install

This repository is a one-plugin marketplace, laid out like `anthropics/claude-for-legal`. In Claude Code:

```
/plugin marketplace add /path/to/fairness-opinion-legal      # a local clone, or bsovocool16/fairness-opinion-legal
/plugin install fairness-opinion-legal@fairness-opinion-legal   # choose user scope when asked
```

The Word renderer's one npm package installs itself the first time outputs are made (node and npm needed); by hand:
`cd <plugin>/scripts/redline && npm install`. The commands also work outside a session as `claude plugin marketplace add ...` and
`claude plugin install ...`, including with the Claude Code binary bundled in the desktop app.

### Prerequisites

Claude Code (the desktop app's Code tab or the `claude` CLI) on a plan that includes Opus, which drafts the section. On a Mac:

```
xcode-select --install                 # once; compiles the bundled Apple Vision OCR for image-only board books
brew install poppler pandoc node       # pdftotext for PDFs, Word inputs, the docx renderer
brew install --cask libreoffice        # optional: PDF versions of the outputs
pip3 install requests beautifulsoup4 lxml
```

On Linux or Windows install the same through the package manager, with `tesseract` in place of the Apple Vision step;
`pip install rapidocr-onnxruntime pypdfium2` is a last-resort OCR that needs no system packages but runs words together
on dense slides. Anything missing degrades rather than fails: text outputs instead of Word, no PDF, or a prompt to supply
the book as text. Then run `/fairness-opinion-legal:cold-start-interview`.

### What you bring

- Your own SEC contact identity (name and e-mail). EDGAR requires it in every request and it goes only to sec.gov.
- The board book and the opinion letter (PDF, PowerPoint, Word or text) and the deal facts intake asks for.
- Optionally the draft proxy, the engagement letter and the relationship memo.

Nothing else ships with the plugin: no precedent bank, no training data. Every precedent is fetched live from EDGAR for
the advisor on your deal.

### Try it first

`/fairness-opinion-legal:demo` needs no setup: it replays a completed run on the bundled public deal
(`examples/distribution-solutions-2026/`, Distribution Solutions Group 2026, William Blair, Rule 13e-3), one stage at a time,
ending with the draft's redline against the section William Blair actually filed. `/fairness-opinion-legal:demo --live`
runs the whole chain for real on the same board book: OCR of the 32 slides, the EDGAR search, shell, draft and redline,
about ten minutes and a few hundred thousand tokens.

## Inputs, and what is not public

The method was learned from public filings: board books filed as exhibit (c) to Schedule 13E-3, opinion letters filed as
proxy annexes, and the sections as filed. Two inputs a drafter has in practice are not public and were never part of the
training: the engagement letter (fee and expense terms) and the advisor's relationship disclosure memo (prior and current
relationships with the parties). Intake asks for both as optional uploads; with them the fees-and-relationships paragraph is
drafted from the source rather than left for the reviewer.

## Layout

```
.claude-plugin/marketplace.json           marketplace manifest (one plugin)
fairness-opinion-legal/                   the plugin
.claude-plugin/plugin.json   manifest
CLAUDE.md                    practice-profile template (the interview writes the live copy to ~/.claude/plugins/config/fairness-opinion-legal/)
skills/<name>/SKILL.md       one skill per stage
scripts/                     precedent search, book classifier, shell builder, self-scorer, glossary, text extraction, OCR
scripts/redline/             the Litera-style comparison tool (docx + pdf)
references/                  the drafting task texts, the scoring, and regime notes
agents/                      the named end-to-end agent
```

Copyright 2026 Benjamin Sovocool. Private repository.
