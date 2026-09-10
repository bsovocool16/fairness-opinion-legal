---
name: cold-start-interview
description: >
  Set up the fairness-opinion-legal practice profile: who you are, the SEC contact
  identity that EDGAR requires, precedent and drafting defaults, output formats and
  the gates. Use on fresh install, when the profile still has [PLACEHOLDER] markers,
  when the user says "set up", "configure", "onboard", or before the first deal.
argument-hint: "[--redo | --check-tools]"
---

# /cold-start-interview

1. Read `~/.claude/plugins/config/fairness-opinion-legal/CLAUDE.md`. Missing or with `[PLACEHOLDER]` markers: run the interview. Populated: skip unless `--redo`. `--check-tools`: only re-run the tool check and rewrite `## Available integrations`.
2. Use `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md` as the section scaffold. Write the completed profile to the config path, creating directories as needed.
3. Never write a profile with silent gaps: list what was skipped before writing, and mark it `[PENDING]`.

## Before the interview

Show this, then wait for the pick:

> **fairness-opinion-legal drafts the financial-advisor opinion section of a merger proxy** from the advisor's board book and opinion letter, using the advisor's own filed precedents. Not your area? Stop here.
>
> **2 minutes** gets your name and role, the SEC contact identity, and working defaults for everything else. **10 minutes** adds your firm's house style, a shell library if you keep one, your reviewer, and which gates you want on.
>
> Quick or full?

Then orient in three sentences: the profile is a plain-text file every skill reads; everything can be changed later with `/fairness-opinion-legal:customize`; the profile is built only from what the user types or shares here, never from other conversations or memory.

## Interview pacing

- Two or three answerable prompts per turn, counting subparts.
- Anything longer than a sentence: "paste it, share a path, or give me the short version."
- Say "pause" to stop; write the partial profile with `<!-- SETUP PAUSED AT: [section] -->` and `[PENDING]` markers; resume from there next time.

## Part 0: role and tools (both paths)

1. Name, role, practice setting, firm or company.
2. **SEC contact identity.** Explain in one sentence: the SEC requires automated clients to send a User-Agent naming a person and an email; precedent search will not run without one. Ask for name and email. Store it; never reuse it for anything but EDGAR requests.
3. Tool check: run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check_tools.py`. Report each tool as present or missing and what degrades without it (no `pdftotext`: board books must be supplied as text; no LibreOffice: no PDF redlines; no node modules in `scripts/redline`: no docx outputs, ask the user to run `npm install` there). Write the table to `## Available integrations`.

Quick path: accept every `[DEFAULT]`, write the profile, close with: "Done. Run `/fairness-opinion-legal:pipeline` for a deal. When an output feels off, the profile line that drives it is named in the output."

## Part 1: full path

4. Reviewer: who signs off before anything leaves the building.
5. House style: does the firm depart from the advisor's precedents anywhere (section title, table format, how reference items are placed)? Paste a prior section the firm drafted if one exists; extract the departures, do not copy deal facts.
6. Shell library: a folder of the firm's own shells by advisor, or none. If given, note that intake will offer it alongside EDGAR results.
7. Drafting mode: objective (default) or procedure. One sentence each; see `references/drafting-modes.md`. Then the drafter model: opus (default, the tested drafter) or fable (the top model; for unusual deals; costs more). Write both into the Drafting section.
8. Gates: which of the four stay on. Default: intake confirm, precedent-set approval, final sign-off on; shell review off.
9. Output formats and the work-product header text.

## Before writing

List every skipped question. Ask whether to fill any now. Then write the profile and show a five-line summary.

## What it does NOT do

- It does not read the user's other conversations, memory, or files not shared here.
- It does not verify the SEC identity beyond its format; a wrong contact is the user's to fix.
