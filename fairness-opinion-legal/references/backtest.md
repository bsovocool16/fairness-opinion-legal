# Held-out backtest: protocol, metrics and first results

`scripts/backtest/backtest.py` runs the ticker-to-proxy lifecycle **blind** on a completed going-private deal, as of the day
before it became public, and then scores each stage against what was actually filed: the historical financials, the
management projections, the advisor's final board book, its fairness opinion letter, and the proxy's summary of its analyses.

```
spec.json ─► blind ─► <bt>/blind/        (the lifecycle, point-in-time; never reads sealed/)
          ─► seal  ─► <bt>/sealed/       (proxy, section, letter, projections, final book, truth.json)
          ─► audit ─► <bt>/audit.json    (leakage checks on blind/)
          ─► score ─► <bt>/scorecard.json, scorecard.md
```

`all` runs them in that order, so the filed record does not exist on disk until the blind run is finished.

## Choosing a held-out deal

A deal qualifies when:

1. **It is a completed Rule 13e-3 transaction with a cash price.** A Schedule 13E-3 must file every report the advisor gave the
   committee as exhibit (c), so the advisor's final board book is public, not only the proxy's summary of it.
2. **It was announced after the drafter model's training cutoff.** Otherwise the drafter may have read the filed section, and
   the section score measures recall rather than drafting. The spec records `drafter_training_cutoff`; the audit warns when
   the announcement is on or before it.
3. **It was not used in development.** DSGR and WTS are excluded. DSGR also has a real Schedule 13E-3 (filed 2026-09-01), so
   the DSGR dev runs are not a clean test of anything.
4. **A DCF is meaningful**: an operating company valued on EBITDA and cash flow, not a bank, insurer, REIT or pre-revenue biotech.
5. **The advisor has filed sections before the opinion date** (precedent search needs them).

Candidates found on 2026-11-23 by EDGAR full-text search of SC 13E3 and DEFM14A filings since June 2025:

| deal | advisor | announced | status | fit |
|---|---|---|---|---|
| **Utz Brands (UTZ)**, Intersnack, $14.25 | Citigroup Global Markets | 2026-07-21 | closed 2026-11-20 | **chosen**: after the training cutoff, final book has a text layer, rich projections table |
| Baldwin Insurance Group (BWIN), $32.50 | Ardea Partners, Perella Weinberg | 2026-09-14 (leak 2026-06-17) | vote pending | backup; two advisors, and a leak date tests the unaffected-date rule |
| Select Medical (SEM), Clearwater Analytics (CWAN), European Wax Center (EWCZ) | various | Dec 2025 to Mar 2026 | closed | before the training cutoff; Yahoo has already dropped their prices |
| Bowhead, Personalis | various | Aug 2026 | pending | insurer / loss-making: a DCF is not the right test |

## The held-out protocol (what the blind run may know)

| input | allowed | how it is enforced |
|---|---|---|
| Signing terms: offer price, buyer, advisor, addressee, regime, opinion date | yes; the advisor knew them when it opined | from the spec |
| XBRL financials | only facts **filed** on or before the cutoff; a later restatement is dropped | `fetch_company.point_in_time`; audit checks every `filed` date |
| Company name | as it stood on the cutoff (a company taken private is often renamed) | `name_as_of` (EDGAR former names) |
| Prices, 52-week range, beta, Treasury yield | closes up to the cutoff, two years for beta | `price_block`; audit checks every price date |
| Delisted target's prices | a cached chart, cut at the cutoff before it is committed | `PRICE_CACHE`, `examples/backtest/utz-prices/` |
| Precedents | the advisor's filed sections dated before the opinion; never the deal's own filings | `find_precedents(before=opinion date)`; audit checks dates and accession numbers |
| Peers (assisted mode only) | a list from a document **filed before the cutoff**, cited in the spec | `--assisted` refuses a source filed after the cutoff |
| Anything under `sealed/` | never | `all` seals after the blind run; audit fails if a filed range or the record's accession numbers appear in blind outputs |

**Auto** mode takes no judgment input at all. **Assisted** mode adds only what an analyst could have chosen before the
cutoff from public filings; for Utz, the compensation peer group in its own 2026 proxy statement (filed 2026-03-12).

Known residual leak: peer candidates come from today's SEC ticker list, so a peer delisted since the cutoff cannot be picked
(survivorship). The audit warns about it on every run.

## Metrics, stage by stage

| stage | metric | why |
|---|---|---|
| fetch | unaffected price; fiscal-year revenue, operating income and net income to the parent against the proxy's summary financials; LTM EBITDA against the advisor's LTM Adjusted EBITDA | did we read the company right |
| projections | absolute % error by year, revenue and EBITDA, against management's projections; CAGR of each | our projections are derived from history; this measures how far that is from management's plan |
| valuation | per analysis: IoU of our per-share range with the advisor's (overlap / union), midpoint error, and whether the offer sits below, within or above the range in both | IoU rewards both location and width; offer side is what the opinion turns on |
| valuation | WACC and perpetuity growth gap in basis points; exit and applied multiples; peer-set Jaccard by normalized name | where a range difference comes from |
| valuation | recall: share of the advisor's core (non-reference) analyses the pipeline builds | analyses we do not attempt score as misses |
| deck | analyses in our book against the advisor's final book: precision, recall | |
| letter | 6-word phrases (names and numbers masked) shared with the filed letter, each direction; required elements (date, fairness conclusion, reliance, no independent verification, fee, signature, "unaffiliated" holders for 13e-3) | |
| section | share of the filed section's phrases the draft carries; analyses presented precision and recall; length ratio | the same signals as `scoring.md`, run once `section-draft` has drafted on the blind folder |
| bottom line | both letters reach the same conclusion | necessary, not sufficient: see the Utz result |

## First results: Utz Brands (2026-11-23)

Audit passed on both runs. Full scorecards are in the project files (`backtest/utz/`).

| | auto | assisted (peers from Utz's 2026 proxy) |
|---|---|---|
| model stage | **stopped**: one SIC peer (Medifast), and the Comps tab's quartile formulas error with one peer | ran through handoff |
| peer Jaccard vs Citi | 0.00 | 0.67 (6 of Citi's 7; Post Holdings missing) |
| trading range, premiums IoU | 0.97, 0.97 | 0.97, 0.97 |
| comps, DCF ranges | negative | negative ($-5.44 to $-3.61; $-9.63 to $-1.63) vs Citi's $5.70-$9.00 and $10.60-$14.80 |
| revenue projections, mean abs error | 6.3% | 6.3% |
| EBITDA projections, mean abs error | 56% | 56% |
| deck analyses precision / recall | – | 0.80 / 0.57 (no precedents, price targets or future share price; an LBO Citi did not show) |
| letter: filed phrases carried / elements missing | – | 0.06 / "unaffiliated" holders |
| bottom line | – | agrees (fair), but only because the offer sits above every range, including the negative ones |

What the backtest found, in order of effect:

1. **Up-C structure.** Utz's Class A stock is 62.4% of the economic interest; the rest is Class V units held by the founders.
   The model takes Class A shares only (88.3 million) **and** subtracts the book noncontrolling interest ($628 million) for
   the units, so equity value goes negative. Citi values the whole company and takes 62.4%. The units should be counted as
   shares (or the NCI valued at market), not deducted at book value.
2. **Reported vs adjusted EBITDA.** LTM EBITDA from EBIT plus D&A is $108 million; Citi's LTM Adjusted EBITDA is $219 million
   (impairments, transformation costs, stock compensation added back). Every EBITDA-based number inherits the gap, and the
   target appears to trade at 19.1x where the market sees about 10x.
3. **SIC peers.** SIC 2090 had one usable peer. A pre-cutoff, leak-free peer source exists in every target's own proxy
   statement (the compensation peer group) and recovered six of Citi's seven peers here; it could be the automatic fallback.
4. **One peer stops the model** (`#VALUE!` and `#DIV/0!` in the Comps quartiles). The thin-peer flag fires, but the formulas
   should degrade rather than error.
5. **Analyses not built.** Precedent transactions, analyst price targets and future share price are in Citi's section; the
   lifecycle builds none of them (stated in `lifecycle.md`), so valuation recall is 0.67 at best.
6. **The 13e-3 letter** does not address fairness to the "unaffiliated" stockholders, which a 13e-3 opinion does.

## Running it

```
export EDGAR_UA="Name email"
python3 scripts/backtest/backtest.py all examples/backtest/utz.json <bt dir>                 # auto
python3 scripts/backtest/backtest.py blind examples/backtest/utz.json <bt dir> --assisted    # then audit, score
python3 scripts/backtest/backtest.py blind ... --precedents                                   # also the precedent search, before the opinion date
```

To score the proxy section, run `section-draft` on `<bt dir>/blind` (it is an ordinary deal folder after handoff), then
`score` again. A new held-out deal is a new spec: copy `examples/backtest/utz.json`, fill the signing terms and the record's
accession numbers and documents, and cache the target's prices if Yahoo no longer serves the ticker.
