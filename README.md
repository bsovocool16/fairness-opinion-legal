# fairness-opinion-legal

A Claude plugin that drafts the "Opinion of [Financial Advisor]" section of a merger proxy statement the way a
transactional associate does it: find the advisor's own filed sections, pick the closest one, change only the deal facts,
and hand the reviewer a clean draft with a redline. Built from public EDGAR filings only. Every output is a draft for
attorney review, not legal advice.

> The method was developed and tested in a private research repository across seven iterations on 24 held-out deals;
> `references/scoring.md` summarizes what is scored and the results.

An independent project by Benjamin Sovocool, not affiliated with or endorsed by Anthropic. It follows the conventions of
the [claude-for-legal](https://github.com/anthropics/claude-for-legal) plugins so that it fits the same workflow.

## What it does, in order

| stage | skill | what happens | gate |
|---|---|---|---|
| 0 | `cold-start-interview` | practice profile: who you are, the SEC contact identity, defaults, gates | once |
| 1 | `deal-intake` | asks the regime (Rule 13e-3 or conventional) first, then prompts for the board book, the opinion letter, the deal facts and the optional inputs; reads the book's analyses | confirm |
| 2 | `precedent-search` | finds the advisor's filed sections on EDGAR, verifies each, ranks by regime, coverage and recency | approve the set |
| 3 | `shell-builder` | picks the base section and splices in same-advisor paragraphs for analyses it lacks, with provenance | optional |
| 4 | `section-draft` | marks the shell up with the deal's facts, scores itself against the package, writes the log | |
| 5 | `redline` | clean draft plus a redline against the shell (and against any prior draft) | reviewer sign-off |
| – | `feedback` | saves a correction or preference the moment you give it, scoped to all deals, one advisor or one deal; every later stage reads the notes that apply | |
| – | `demo` | replays a completed run on the bundled public deal stage by stage, through to a comparison with the section as filed; `--live` runs the chain for real on the same inputs | |

`pipeline` runs 1 to 5 in sequence, stopping at every gate the profile turns on. A correction given at any gate is saved by `feedback` and applied to later deals. The drafter runs on Opus by default; `--model fable` on `pipeline`, `section-draft` or `demo --live`, or `Drafter model: fable` in the profile, switches it. `proxy-glossary` is the optional step
between 1 and 4 when a draft proxy exists. `matter-workspace` keeps deals separate. `customize` edits the profile.

## Install

This repository is a one-plugin marketplace, laid out like `anthropics/claude-for-legal`. In a Claude Code terminal session
(the `claude` command), type:

```
/plugin marketplace add bsovocool16/fairness-opinion-legal
/plugin install fairness-opinion-legal@fairness-opinion-legal
```

Choose user scope when asked. From a clone or the zip, give the folder path in place of `bsovocool16/fairness-opinion-legal`.
The same two commands run from any shell as `claude plugin marketplace add bsovocool16/fairness-opinion-legal` and
`claude plugin install fairness-opinion-legal@fairness-opinion-legal --scope user`. The desktop app's Code tab does not offer
the `/plugin` dialog, but it shares the configuration, so a plugin installed either way is available in its next session.

The Word renderer's one npm package installs itself the first time outputs are made (node and npm needed); by hand:
`cd <plugin>/scripts/redline && npm install`. The commands also work outside a session as `claude plugin marketplace add ...` and
`claude plugin install ...`, including with the Claude Code binary bundled in the desktop app.

After changes to the clone, refresh an install with `claude plugin marketplace update fairness-opinion-legal` and
`claude plugin update fairness-opinion-legal@fairness-opinion-legal`; the updater only picks up a new version number, so bump
`fairness-opinion-legal/.claude-plugin/plugin.json` first.

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
CLAUDE.md                    practice-profile template (the interview writes the live copy to ~/.claude/plugins/config/fairness-opinion-legal/,
                             next to feedback.md, the user's corrections for later runs)
skills/<name>/SKILL.md       one skill per stage
scripts/                     precedent search, book classifier, shell builder, self-scorer, glossary, text extraction, OCR
scripts/redline/             the Litera-style comparison tool (docx + pdf)
references/                  the drafting task texts, the scoring, and regime notes
agents/                      the named end-to-end agent
```

## License

Copyright 2026 Benjamin Sovocool. Licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE.md): free to use, copy and
modify for noncommercial purposes, which covers personal use, evaluation, research, teaching and use by noncommercial
organizations. Any commercial use, including use in a law firm's or a bank's practice, needs a license from the author.

Required Notice: Copyright 2026 Benjamin Sovocool
