---
name: deal-intake
description: >
  Onboarding for one deal: asks whether it is a Rule 13e-3 going-private or a
  conventional transaction, then prompts for each input in order (board book,
  opinion letter, deal facts, and the optional draft proxy, engagement letter and
  relationship memo), extracts the text, reads which analyses the book presents,
  and writes the deal folder. Use when the user has a board book or a fairness
  opinion to work from, says "new proxy section", "intake", "here's the deck",
  or starts the pipeline on a deal that has no facts.json yet.
argument-hint: "[deal code]"
---

# /deal-intake

1. Resolve the deal: `$ARGUMENTS`, else the profile's `Active deal:`, else run `/fairness-opinion-legal:matter-workspace new`.
2. Ask the regime question first, then collect the inputs in the order below, one or two prompts per turn, waiting for each upload.
3. Run the scripts, show the intake summary, and stop at the intake gate if the profile has it on.

## Why the regime comes first

A Rule 13e-3 transaction (an affiliate, a controlling holder or management on the buy side; a Schedule 13E-3 is filed) carries the Item 1015 disclosure of the advisor's report, so the opinion section runs longer and reads differently from a conventional third-party deal's. The precedents must come from the same regime, and that decision cannot be read reliably from the book. Ask:

> Is this a Rule 13e-3 going-private (an affiliate, controlling holder or management buyer; a Schedule 13E-3 will be filed) or a conventional transaction? If you are not sure, tell me who the buyer is and I'll say which it looks like, but you decide.

Record the answer in `facts.json` as `regime: "13e-3" | "conventional"` and in `deal.md`.

## Inputs, in order

Prompt for each; say what it is for; accept a path, a paste, or "skip". Required inputs cannot be skipped; say why.

1. **Board book** (required): the advisor's presentation to the board or committee at the opinion meeting, PDF or PowerPoint. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_text.py <file> inputs/book.txt`. If it reports pages with no text layer (scanned or image-only decks are common), run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ocr.py <file> inputs/book_ocr.txt`: Apple Vision on a Mac (compiled once from the bundled Swift source), otherwise RapidOCR (`pip install rapidocr-onnxruntime pypdfium2`), otherwise tesseract. Say which backend ran and how many pages. The classifier and the drafter read both files, so a book with a partial text layer keeps both.
2. **Opinion letter** (required unless not yet delivered): the signed letter, or the draft. Extract to `inputs/opinion_letter.txt`. If not yet delivered, record `letter: "pending"`; the review list and assumptions will be drafted from the book and the advisor's precedents and flagged.
3. **Deal facts** (required): target legal name and ticker; buyer and buyer type (strategic | sponsor | controlling holder | management); consideration form and per-share price; addressee (board or special committee); opinion date; pricing date if different; the advisor's legal name as it signs; the advisor's role (sole | co-advisor). Prefill anything the letter states and ask only for the rest. Write `facts.json`.
4. **Draft proxy or merger agreement** (optional): for the defined terms. If provided, run `/fairness-opinion-legal:proxy-glossary` after intake. Say: without it, the drafter introduces terms itself and the reviewer conforms them.
5. **Engagement letter** (optional, not public): fee, contingent portion, opinion fee, expense cap. Store under `inputs/`; the fees paragraph is drafted from it. Without it the fee sentence is left with the reviewer's marker.
6. **Relationship disclosure memo** (optional, not public): the advisor's prior and current relationships with the parties and fees received. Store under `inputs/`; the relationships paragraph is drafted from it. Without it the paragraph carries the advisor's precedent language and a reviewer's marker, never an invented "no relationships" statement.
7. **Firm shell** (optional): a prior section the firm drafted for this advisor. Copy into `precedents/` with a `firm_` prefix; it competes with the EDGAR precedents in ranking.

## After the uploads

Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/classify_book.py <deal dir>`. It writes `deck_analyses.json` (analysis, status core or reference, pages) and prints the regime the book text suggests. Show:

```
Deal <code> — <target> / <advisor> — regime: <as stated> (book text suggests: <hint>)
Analyses the book presents: comps (core, pp. 12-15), precedents (core, pp. 16-18), dcf (core, pp. 19-21), targets (reference, p. 9) ...
Inputs: book (N pages, M without text layer), letter <yes|pending>, draft proxy <yes|no>, engagement letter <yes|no>, relationship memo <yes|no>, firm shell <yes|no>
```

Ask the user to confirm the regime and the analysis list (add or strike). Write `deal.md`, append to `history.md`. Hand off:

```yaml
handoff:
  deal_dir: ~/.claude/plugins/config/fairness-opinion-legal/deals/<code>
  next: precedent-search
  regime: 13e-3 | conventional
  analyses: [comps, precedents, dcf, ...]
  before: <opinion date>
```

## What it does NOT do

- It does not decide the regime; it asks, and records what the book suggests only as a hint.
- It does not invent facts the inputs lack; a missing fact is recorded as missing and surfaces in the draft's log.
- It does not read files outside the deal folder or the paths the user gave.
