---
name: feedback
description: >
  Save a correction or preference for later runs. Use whenever the user says
  "never", "always", "next time", "from now on", "we don't do that", "our house
  style is", "remember this", "note for next time", or corrects an output at a
  gate; also "show my notes", "forget that note". The note is dated, scoped to
  all deals, one advisor or this deal, and kept in the user's feedback file;
  every stage reads the notes that apply before it starts.
argument-hint: "[<note> | list | remove <id>] [--scope all|advisor:<name>|deal:<code>] [--stage intake|search|shell|draft|redline]"
---

# /feedback

1. Take the note from `$ARGUMENTS` or from what the user just said. Restate it in one sentence as an instruction for a future run: what to do, not what went wrong.
2. Scope: a note that names an advisor or is plainly about one advisor's form is `advisor:<name>`; a note about this deal only is `deal:<code>`; anything else is `all`. Stage: the one it changes (intake, search, shell, draft, redline) or all. Ask only when genuinely unclear; otherwise state the choice and let the user correct it.
3. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/feedback.py add "<note>" --scope <scope> --stage <stage> --from <active deal code>`. Show the line written and the file. A note that should stay with this deal alone takes `--deal-level <deal dir>` and lives in the deal folder instead.
4. If the note contradicts an earlier one, say so and offer `feedback.py remove <id>` for the older one.

`list`: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/feedback.py list`, or `list --for <deal dir>` for what applies to the active deal. `remove <id>` deletes one note.

## How the notes are used

Every stage skill starts with `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/feedback.py for <deal dir> --stage <stage>` and follows what it prints; the drafting log lists the notes applied. Notes are the reviewer's standing corrections: they win over the plugin's defaults and over the precedents' form, but never over the inputs. A note cannot add a fact the book or the letter lacks.

## What it does NOT do

- It does not change the practice profile (`customize` does), the precedents or the scoring.
- It does not apply a note to a draft already delivered; rerun the stage.
