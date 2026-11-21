# Ticker to proxy: stages, interfaces and drafting conventions

`skills/ticker-to-proxy` runs `scripts/lifecycle/ticker_to_proxy.py`, which chains seven stages. Each stage reads only JSON
files and workbook cells written by earlier stages, and writes its own files under `<deal>/lifecycle/`. A stage can be re-run
alone (`ticker_to_proxy.py stage <name> <deal>`), tested alone, or replaced, as long as its output keeps the schema.

```
ticker ─ fetch ─► company.json ─ terms ─► deal_terms.json ─ model ─► model.xlsx ─(LibreOffice recalc)─► valuation.json
                                                                       │                                   │
                                                                     check ─► model_check.json            deck ─► board_book.pdf, deck.json
                                                                                                               │
                                                     handoff ◄─ opinion_letter.txt, letter.json ◄─ letter ◄────┘
                                                        │
             facts.json, inputs/book.pdf, inputs/book.txt, inputs/opinion_letter.txt, deck_analyses.json
                                                        │
                       precedent-search ─► shell-builder ─► section-draft ─► redline        (the existing pipeline)
```

## Files and schemas

| file | schema | written by | key fields |
|---|---|---|---|
| `company.json` | `company/1` | fetch | `target` and each of `peers`: `name`, `ticker`, `cik`, `sic`, `annual[]` (target only: `fy`, `period_end`, `revenue`, `ebit`, `da`, `capex`, `nwc`, `interest`, `pretax`, `tax`, `net_income`, `sources`), `ltm.values`, `balance` (`cash`, `debt`, `nci`, `preferred`, `as_of`), `shares_out_mm`, `price` (`last`, `date`, `high_52w`, `low_52w`, `avg_30d`, `history_1y`, `beta_raw`); `market.risk_free`; `peer_basis`; `synthetic` for the fixture |
| `deal_terms.json` | `deal_terms/1` | terms | `target`, `ticker`, `advisor`, `addressee`, `buyer`, `buyer_type`, `consideration`, `unaffected_price`, `unaffected_date`, `offer_price`, `premium`, `opinion_date`, `regime`, `codename`, `hypothetical: true` |
| `valuation.json` | `valuation/1` | model | `ranges` (`trading_range`, `premiums`, `comps`, `dcf_pgr`, `dcf_exit`, `lbo`, each `low`/`high` per share); `cells` (every output as `{value, cell}`, the cell being the workbook address it was read from); `errors`; `flags`; `assumption_basis` |
| `model_check.json` | list | check | `{rule, cell, detail}` per finding; empty when the model passes |
| `deck.json` | `deck/1` | deck | `pptx`, `pdf`, `pages[]` (`page`, `title`, `analysis`), `analyses` |
| `letter.json` | `letter/1` | letter | `offer_vs_ranges[]`, `supported`, `written`, `forced`, `markers` (the `[bracketed]` items left for the reviewer) |
| `manifest.json` | – | every stage | `stages.<name>.status` ok, stopped or failed, with time and detail |

Units throughout: $ in millions, shares in millions, per-share figures in dollars.

The rule that keeps the documents consistent: **no number downstream of the model is computed in Python.** The deck and the
letter read `valuation.json`, which holds values read back from the recalculated workbook. Change an assumption in Excel,
run `stage revalue`, and the book follows.

## Drafting conventions the model follows (and `check_model.py` enforces)

These are the conventions a bank analyst is held to. They are what lets a reviewer trust a model without re-deriving it.

| rule | convention | why |
|---|---|---|
| C1 | **Blue** font for every typed number (an input or a reported figure); **black** for a formula on the same tab; **green** for a formula that pulls from another tab. Never a formula in blue. | A reviewer can see at a glance what was assumed versus computed, and which cells to change. |
| C2 | **No numbers typed inside formulas** (`=B5*1.05` is the classic error). Only structural constants pass: 0, 1, 2, 3 and 4 (quartile arguments), 0.5 (mid-year), 12 (months), 365 (days). | A buried hardcode silently survives every change to the inputs. |
| C3 | Typed numbers live only on the **input tabs**: Assumptions, Historicals, Comps (each peer's market data) and WACC (peer betas). The DCF, LBO, Sensitivity and Summary tabs are all formulas. | One place to change each assumption. |
| C4 | Every tab states its **units** under the title. | Mixed units are the most common silent error. |
| C5 | After recalculation, **no error values** (`#DIV/0!`, `#REF!`, `#NAME?`, `#VALUE!`, `#N/A`, `#NUM!`, LibreOffice `Err:5xx`). | |
| C6 | **No orphan inputs**: every input on Assumptions feeds some formula. | An input nobody reads is a trap for the next person who changes it. |

Other conventions the builder applies (not machine-checked):

- Each input carries its **source or basis** in the column beside it: the XBRL tag and filing for reported figures, the method for derived defaults (e.g. "3-year average EBITDA margin"), "judgment input" for the rest.
- **Historicals** show the reported figures; **margins and percentages** are formulas under them, so the 3-year averages on the Assumptions tab are live references a reviewer can trace.
- **DCF:** unlevered free cash flow = EBIT less taxes on EBIT, plus D&A, less capex, less the increase in net working capital. Stock-based compensation is treated as a cash cost (not added back). A **stub period** prorates the first projection year from the valuation date, and the **mid-year convention** is an on/off input. Both terminal value methods are shown, each with the **implied** figure of the other (perpetuity → implied exit multiple; exit multiple → implied perpetuity growth) as a cross-check.
- **WACC:** CAPM cost of equity with the peer median **unlevered beta** (Hamada), relevered at a target debt-to-capitalization; risk-free rate is the 10-year Treasury.
- **Sensitivity grids** are explicit formulas, not Excel data tables, so they compute in any spreadsheet program. The center cell equals the DCF tab's midpoint value; the tests assert it.
- **Signs:** costs and uses of cash are negative in the cash flow build ("Less: ..."), so every subtotal is a plain sum.
- **Summary** (football field) carries each analysis's low and high per share and the offer price; the chart is driven by those cells.

## Limits, stated in the outputs

- Projections are derived from reported history, not management's; they are labeled illustrative on the model, the book and in the letter's review list.
- No precedent transactions analysis or analyst price targets (no free public source). The book never mentions either, so the classifier does not report them.
- Shares are basic shares from the latest 10-Q/10-K cover page, not fully diluted.
- The premiums paid range is a judgment input, not a premiums study.
- The LBO charges interest on the opening debt throughout (no circularity); it is a screen of a sponsor's ability to pay, not a financing model.
