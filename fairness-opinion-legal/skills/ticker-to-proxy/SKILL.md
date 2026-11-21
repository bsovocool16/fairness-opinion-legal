---
name: ticker-to-proxy
description: >
  Demo of the whole deal lifecycle from a stock ticker: public data from SEC
  EDGAR, a banker-convention Excel valuation model, a board book, a fairness
  opinion letter, then the proxy's "Opinion of [Advisor]" section through the
  usual pipeline. Every deal term is hypothetical. Use when the user says
  "ticker to proxy", "start from a ticker", "build the model and the book",
  "run the lifecycle", or names a ticker and wants the deal documents.
argument-hint: "<TICKER> [--advisor <name>] [--premium 0.30] [--buyer-type sponsor|strategic|controlling holder|management] [--peers A,B,C]"
---

# /ticker-to-proxy

Everything this produces is illustrative. Each document carries the line "ILLUSTRATIVE — HYPOTHETICAL TRANSACTION ... Not prepared, reviewed or endorsed by <advisor> or by <target>". Never remove it, and never present the outputs as an advisor's work product.

## Before running

1. Profile: the SEC contact identity is needed (EDGAR requires one). If `~/.claude/plugins/config/fairness-opinion-legal/CLAUDE.md` is missing or its contact is a placeholder, ask only for a name and e-mail and export `EDGAR_UA="Name email"` for this run.
2. Ask in one prompt, with defaults the user can accept as a block:
   - the **advisor** (legal name as it signs; its filed sections on EDGAR become the precedents, so pick a bank in `scripts/edgar_precedents.py` BANK_PHRASES, e.g. "Centerview Partners LLC", "Evercore Group L.L.C.", "Goldman Sachs & Co. LLC")
   - the **buyer** and buyer type (default "Hypothetical Parent, LLC", sponsor). A controlling holder or management buyer makes it Rule 13e-3, addressed to a special committee.
   - the **premium** to the unaffected price (default 30%), or a fixed offer price
   - optionally the **peers** (`--peers`); otherwise they are chosen by SIC code and revenue size, and shown for approval at the model gate
3. Deal folder: `<deals folder>/<ticker lower>-hypo-<yyyy>` (the profile's deals folder, else `~/.claude/plugins/config/fairness-opinion-legal/deals/`).

## Run

`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/lifecycle/ticker_to_proxy.py run <TICKER> <deal dir> --advisor "<name>" [--buyer ...] [--buyer-type ...] [--premium ...] [--peers ...]`

It runs seven stages and stops at the first that fails (`manifest.json` records each). Narrate each one in a line:

| stage | what it does | show the user |
|---|---|---|
| fetch | SEC XBRL financials, prices, 2-year weekly betas, peers, 10-year Treasury | target name, SIC, peers chosen and why |
| terms | the hypothetical deal: unaffected price and date, offer price | unaffected price, offer price, premium, regime |
| model | `model.xlsx`, recalculated in LibreOffice; `valuation.json` read back from the cells | the six ranges; any reviewer flags |
| check | drafting-convention audit (`references/lifecycle.md`) | pass, or the findings by cell |
| deck | `board_book.pptx` and `.pdf`, every number from `valuation.json` | page list |
| letter | `opinion_letter.txt` and `.docx` | how the offer sits against each range |
| handoff | `facts.json`, `inputs/`, `deal.md`, `deck_analyses.json` | the classifier's analysis table |

**Gate (model):** after the model stage, show the ranges, the peers and the key assumptions (WACC, perpetuity growth, exit multiple, selected multiple range, LBO leverage and IRR) and offer to change any of them. Read out every `flag:` line the model stage printed (also in `valuation.json` `flags`) before anything else: a target trading outside its peers' range, fewer than three peers, or comps and DCF midpoints far from the market price mean the "fair" result is an artifact of the peers or the illustrative projections, and the user should name peers (`--peers`) or adjust the assumptions before going on.
- An assumption: the user edits the blue cell on the Assumptions tab of `lifecycle/model.xlsx` (or tells you, and you set it with openpyxl keeping the blue font). Then `stage revalue`, and `stage check`, `deck`, `letter`, `handoff` in turn. Do not re-run `stage model`: it rebuilds the workbook from scratch and drops hand edits.
- The peers: `stage fetch --ticker <T> --peers A,B,C`, then every later stage.

**The letter stops** when the offer is below the low end of most valuation ranges, because an advisor would not render the opinion. Tell the user which ranges the price misses, and offer: a higher premium (`stage terms --premium ...` then the later stages), different assumptions, or `--force` to write it anyway for the demo.

## Then the proxy section

The handoff leaves the folder as `deal-intake` would. Continue with the `pipeline` skill from `precedent-search` (the intake gate is the analyses table the handoff printed): `precedent-search` → `shell-builder` → `section-draft` → `redline`, each as its skill says. The drafter reads the generated book and letter like any other.

## Outputs to send

`lifecycle/model.xlsx`, `lifecycle/board_book.pdf`, `lifecycle/opinion_letter.docx`, and the pipeline's `redline/section.docx` and `redline/redline_vs_shell.pdf`.

## Offline

`--fixture ${CLAUDE_PLUGIN_ROOT}/examples/lifecycle-fixture/company.json` replaces the fetch with an invented company (EXMP) and invented peers, for trying the model, book and letter with no network. Say plainly that its numbers are synthetic. Precedent search still needs EDGAR.

## What it does NOT do

- It does not use management projections; the projections are derived from reported history and labeled illustrative everywhere.
- It does not run a precedent transactions analysis or analyst price targets (no public source); the book does not mention them.
- It does not send, file or share anything.
