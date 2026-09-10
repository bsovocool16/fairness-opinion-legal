---
name: redline
description: >
  Produce the deliverables: a clean draft (.docx and .txt) and a Litera-style
  redline of the draft against the shell, and against any prior draft the user
  supplies, as .docx and .pdf, with the work-product header from the profile.
  Use when the user says "redline", "compare against the shell", "give me the
  clean and the redline", or after the draft in the pipeline.
argument-hint: "[deal code] [--prior <file>]"
---

# /redline

1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/make_outputs.py <deal dir> [--prior <file>]`. It writes `redline/section.docx`, `redline/redline_vs_shell.docx` and `.pdf`, and `redline/redline_vs_prior.*` when a prior draft is given.
2. Show the counts the script prints (words unchanged, deleted, inserted; paragraphs moved) and the `[REVIEWER: ...]` items it found in the draft.
3. Stop at the delivery gate: name the reviewer from the profile and wait for sign-off before the files are sent anywhere.

## Conventions

Blue double underline: text in the draft that is not in the shell. Red strikethrough: shell text the draft dropped. Green: paragraphs the draft carries in a different position. A bar in the left margin marks every changed paragraph. Table rows compare row by row. The redline is direct formatting, not tracked changes: it is for reading and circulating, not for accepting into a document.

## Degraded cases

- No LibreOffice: docx only, say so.
- No node modules in `scripts/redline`: text redline only (`redline/redline_vs_shell.txt`, wdiff style), and tell the user to run `npm install` there.

## What it does NOT do

- It does not send the files. Delivery is the reviewer's act.
