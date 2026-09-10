---
name: matter-workspace
description: >
  Create, list, switch, or close deal workspaces so one deal's book, letter,
  precedents and drafts never mix with another's. Every other skill reads the
  active deal from here. Use when the user says "new deal", "switch deal",
  "list deals", "close deal", or starts work on a transaction without one.
argument-hint: "<new | list | switch | close | none> [code]"
---

# /matter-workspace

1. Read the `## Deals` section of `~/.claude/plugins/config/fairness-opinion-legal/CLAUDE.md`.
2. Dispatch on the first token of `$ARGUMENTS`.
3. Show what changed and confirm before writing.

## Layout

```
~/.claude/plugins/config/fairness-opinion-legal/deals/<code>/
├── deal.md                 code, target, advisor, regime, status, gate log
├── history.md              dated events: intake, search, shell, draft, redline, sign-off
├── inputs/                 book.pdf|pptx and book.txt (+ book_ocr.txt), opinion_letter.txt, draft_proxy.*, engagement_letter.*, relationship_memo.*
├── facts.json              deal facts written by intake
├── deck_analyses.json      the analyses the book presents, by page and status
├── feedback.md             optional: reviewer notes that apply to this deal only (the user's notes for all deals live in the config folder)
├── defined_terms.json/.md  optional glossary from the draft proxy
├── precedents/             <accession>.txt sections, INDEX.json, and any firm shells the user added
├── shell/                  shell_suggested.txt, shell_composite.txt, provenance.json, rationale.json
├── draft/                  section.txt, log.md, selfscore.json
└── redline/                section.docx, redline_vs_shell.docx/.pdf, redline_vs_prior.docx/.pdf
```

Codes are lowercase with hyphens, never the client's name if the matter is confidential in the user's practice (ask). Example: `project-eclipse-2026`.

## Subcommands

- `new <code>`: create the folder, ask three things (a short description; confidentiality level standard | heightened; related deals), write `deal.md` and seed `history.md`. Do not switch automatically; offer to.
- `list`: table of deals with regime, advisor, status, opened date; mark the active one. Archived deals under a separate heading.
- `switch <code>`: set the `Active deal:` line in the profile; show the deal.md summary.
- `close <code>`: append a Closed entry to history.md and move the folder to `deals/_archived/<code>/`. Never delete.
- `none`: detach.

## Rules

- Skills never read another deal's folder.
- Inputs the user marked heightened stay in the deal folder; nothing is copied into the profile or into other deals.
