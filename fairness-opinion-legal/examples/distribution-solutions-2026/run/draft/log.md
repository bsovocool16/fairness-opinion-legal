# Drafting log — Opinion of the Special Committee's Financial Advisor (Project Eclipse)

Deal: Distribution Solutions Group, Inc. (DSGR) / Eclipse Parent Acquisitions, LLC — Rule 13e-3 going-private.
Advisor: William Blair & Company, L.L.C., financial advisor to the Special Committee. Opinion dated July 15, 2026; pricing date July 14, 2026; $35.00 per share in cash.

## 1. Precedent built from

Base / shell: `shell/shell_composite.txt`, which is the ARC Document Solutions, Inc. DEFM14A section (acc. 0001140361-24-043469, 2024-10-16), selected by `shell/rationale.json` (score 1.154). It is the only William Blair 13e-3 precedent in the set, the only one addressed to a Special Committee, and the only one presenting comps + precedents + DCF + LBO + premiums. The composite carried no `[[NOT IN THIS BOOK]]` / `[[BORROWED FROM ...]]` markers (it is byte-identical to `shell_suggested.txt` apart from blank lines), so nothing was borrowed from another precedent's segments.

Secondary language checked and used where the ARC form was silent or where the phrasing is this advisor's standing form:
- SOC Telemed, Inc. (0001213900-22-010811) — the "(i)...(vii)" inline list of selected companies; the LBO framing.
- TESSCO Technologies (0001104659-23-069453) — the sentence on whether William Blair was asked to approach third parties (inverted here, per the opinion letter); the "Fees" form.
- `inputs/opinion_letter.txt` (Annex B) — the examined list, the reliance/assumption paragraphs, the no-opinion paragraph, the 1935 sentence, the Fairness Opinion Committee sentence, the "use and benefit of the Special Committee" sentence, and the definitions of Merger / Merger Consideration / Company Common Stock.

Structure of the filed section, in the order the book presents its work: Historical Stock Price Performance → Research Analyst Price Targets → Selected Public Companies → Selected Precedent Transactions → DCF → LBO → M&A Premiums Paid → General → Fees.

## 2. Added, and why

All additions are driven by `deck_analyses.json`, which marks eight analyses **core**. The base precedent presents five.

| Added | Book source | Why |
| --- | --- | --- |
| **Historical Stock Price Performance** section, snapshot table and 9-row implied premiums table | pp. 9, 11 (`trading_range`, core) | No William Blair precedent in the set has this analysis (`shell/provenance.json`: "no precedent in the set has this analysis"). Written in the advisor's voice from its own "current and historical market prices and trading volumes" bullet. |
| **Research Analyst Price Targets** section and table | p. 13 (`targets`, core) | Same — no precedent in the set carries it. Three firms, ratings, rating dates, CY 2026E Adj. EBITDA estimates, price targets and both premium columns carried in full. |
| **Sensitivity tables** (DCF 3×3 and LBO 3×3) with the words "sensitivity analysis" | pp. 28, 30 (`sensitivity`, core) | The book titles both panels "Sensitivity Analysis"; the base precedent states only a range. Both grids carried in full, plus the range endpoints in the advisor's "resulted in a range of implied equity values of X to Y per share, as compared to the Merger Consideration" form. |
| **Leveraged Buyout Analysis** parameters | p. 30 | $920M total net debt / 5.3x LTM Adj. EBITDA / unitranche at SOFR+500 / CY 2030 Adj. EBITDA of $357M incl. $5M public-company cost savings / 29.5% tax with NOL offset / 10.0% management option pool. The ARC LBO paragraph carried a different parameter set. |
| **Seven-company comps table with six metric columns** | p. 18 | The ARC table has three columns; the book's has Equity Value, Enterprise Value, 2025A-2026E revenue growth, LTM EBITDA margin, EV/LTM Adj. EBITDA, EV/CY 2026E Adj. EBITDA, plus Maximum/Median/Mean/Minimum. All rows and columns carried. |
| **Twelve-transaction table** with Max/Mean/Median/Min and eight footnote markers | pp. 25, 26 | All twelve rows carried. |
| **Definitional sentence** for Merger, Merger Sub, Intermediate, Parent, Merger Agreement, Merger Consideration, Company Common Stock | opinion letter, p. 8 | No `defined_terms.md`/`.json` was supplied — see §5. |
| **Parent named as an entity formed by affiliates of LKCM Headwater Investments, LLC** | p. 8 | Sponsor identified as the book identifies it. No statement is made about the sponsor's relationship with the advisor — see §4. |
| **CY 2026E Adj. EBITDA margin range and median** (6.8%–22.8%, median 12.7%) | p. 20 | Presented as a range and median only, not per company — see §4. |

## 3. Deleted from the precedent, and why

| Deleted | Why |
| --- | --- |
| "William Blair and its affiliates have not performed any financial advisory or other services to ARC, Mr. Suriyakumar or their respective related parties or affiliates in the preceding two years." | This is the "no prior relationships" statement. No `inputs/relationship_memo.*` was supplied, so it cannot be made. Omitted, not replaced. |
| "ARC agreed to reimburse William Blair for certain of its out-of-pocket, documented expenses (including fees and expenses of its counsel and any other independent experts retained by William Blair) reasonably incurred by it in connection with its engagement" | Expense reimbursement is not in the opinion letter or in `facts.json`. The indemnity survives — the letter states it ("the Company has agreed to indemnify us against certain liabilities arising out of our engagement"). |
| "Pursuant to a letter agreement dated May 14, 2024" | The engagement letter and its date were not supplied. Replaced with "Pursuant to the terms of William Blair's engagement". |
| "For more information on the Projections ... see the section of this proxy statement titled 'Special Factors—Certain Effects of the Merger—Certain Unaudited Prospective Financial Information'." | The proxy's section captions are not in the inputs; a cross-reference to a caption I cannot verify would be a placeholder. Omitted. |
| The AlixPartners provenance of the projections, and the second- and third-party preparer language attached to it | The Forecasts here were prepared by the Company's senior management and provided July 8, 2026 (letter clause (d); book p. 5). No third-party preparer. |
| "plus total debt, minority interest and preferred stock, less cash and cash equivalents" → "plus total debt, less cash and cash equivalents" | The book's bridge (p. 9) is equity value + debt − cash. No minority interest or preferred stock is shown. |
| The ARC "reference only purposes" second LBO case (range of total net leverage 2.25x–3.75x at a 20% IRR) | The book runs no second LBO leverage case. |
| ARC's transaction footnotes (pension-adjusted multiples, COVID normalisation, etc.) and its scope recital "(i) analysis of various strategic and financial options ... (ii) a possible business combination with another party" | ARC-specific; replaced with this book's footnotes and with a scope statement supported by the letter and the book. |
| "The Board hired William Blair based on its deep understanding of the Company's business ..." (SOC/TESSCO form) | Not sourced for this deal. |

Retained verbatim apart from deal facts: the all-caps qualification paragraph, the examined-list bullets, the reliance and no-opinion paragraphs, the "The following is a summary of the material financial analyses ..." paragraph, both "Although William Blair compared ..." caveats, both "William Blair noted that the analyzed implied ... was within the range" sentences, the whole **General** paragraph, and the **Fees** paragraph structure. The precedent's own "range of multiples of the selected publicly companies" (sic) is kept verbatim rather than corrected, as it appears in this form in both the ARC and SOC Telemed filed sections.

## 4. Facts the inputs lack — omitted and logged

1. **Advisor's prior relationships.** No relationship memo. The section says only what the opinion letter says: "William Blair is familiar with the Company, and has acted as an investment banker to the Company in connection with the Merger," plus the standing ordinary-course trading sentence. Nothing is said about William Blair's relationships with Parent, LKCM Headwater Investments, LLC, Bryan King or their affiliates, and no "no prior relationships" statement is made.
2. **Engagement letter date.** Not supplied; the "Pursuant to a letter agreement dated ..." opener is dropped. The fee amounts themselves are in `facts.json` (`fee_mm` 2.0; `fee_note` "$2.0mm opinion fee + $4.6mm contingent on closing"), so the fee sentence is complete and **no `[REVIEWER: fee amount]` marker is carried**. The section does not state a combined fee, because the total is a derived figure the inputs do not state.
3. **Expense reimbursement.** Not in the inputs — omitted (see §3).
4. **Per-company CY 2026E Adjusted EBITDA margins** (book p. 20). The page is a bar chart; the seven values (22.8%, 17.6%, 16.8%, 12.7%, 12.6%, 7.5%, 6.8%) cannot be attributed to named companies from either the text layer or the OCR without guessing, so they are presented as a range and a median only.
5. **Period for the $40.85 high / $13.01 low** (p. 11). The chart's period is not stated in either layer, so the section says "over the historical period reviewed" rather than naming a window.
6. **Trading histogram** (p. 12: 18.3m shares / ~2.1x float / $2.0m ADTV over LTM; 43.4m / ~5.0x / $1.7m over three years). Drafted and then cut for length; the page is not among the `trading_range` pages in `deck_analyses.json` and the histogram buckets are a chart, not a table of rows.
7. **Year-by-year unlevered free cash flow** ($63m, $142m, $157m, $166m, $186m; p. 14). Cut for length — that table belongs to the proxy's prospective-financial-information section, not the opinion section. The book's note that cash flows are burdened by stock-based compensation is retained.
8. **Net debt used in the DCF bridge.** The book does not state which net debt figure the DCF subtracts, so the section says "the Company's net debt as of March 31, 2026" without repeating the $685m figure (which is stated in the trading table, where the book states it).
9. **Components of net debt** ($45m revolver, $691m term loan, $0.4m other revolver, $1.3m financing leases, $53m cash; p. 11 fn. 2). Cut for length.
10. **Per-transaction sourcing footnotes** (which 8-K / investor presentation each LTM figure came from). Compressed to the period and the two substantive adjustments ($37.5m Hisco retention bonuses; $51m Roper earnouts excluded) for length. Every LTM period the book states is retained.
11. **"SPRs"** appears in the book's share-count footnotes with no expansion. Carried as written; not expanded.
12. **Oral-then-written opinion.** The inputs establish a July 15, 2026 Special Committee meeting held to consider the Merger Consideration (book p. 2), a written opinion dated July 15, 2026, and a draft Merger Agreement of the same date. The advisor's standing form ("delivered its oral opinion ... subsequently confirmed in its written opinion dated ... prior to the execution of the Merger Agreement") is used on that basis.

### Source conflicts between the text layer and the OCR — text layer used
- Foundation Building Materials enterprise value: text layer **$8,800**, OCR $8,900. The text layer reconciles to the book's own Mean of $6,138 and Median of $4,076; $8,800 used.
- 2030P unlevered free cash flow: text layer **$186**, OCR $136. $186 reconciles to the stated 11.2% CAGR from $109. (Figure ultimately cut per item 7.)
- 60-trading-day ADTV: text layer **$2.65m**, OCR $2.45m. Text layer used.

### Names resolved from the OCR logo row (book p. 18)
The text layer gives the seven selected companies' metrics without names; the OCR gives the logo wordmarks. Resolved to full legal names, ordered by the book's row order (descending enterprise value), with footnote (1) of the book confirming rows 4 and 5:
GRAINGER → W.W. Grainger, Inc.; FASTENAL → Fastenal Company; wesco → WESCO International, Inc.; GAPPLIED → **Applied Industrial Technologies, Inc.** (named in book fn. 1 and in the precedent transactions table); MSC → **MSC Industrial Direct Co., Inc.** (named in book fn. 1); HILLMAN → Hillman Solutions Corp.; SLORAL/GLORAL → **Global Industrial Company** (OCR mangling of GLOBAL; the only industrial/specialty distributor in the size band with net cash, consistent with equity value $1,304m above enterprise value $1,243m).
Research firms likewise resolved from the OCR: Barrington → Barrington Research Associates, Inc.; KeyBanc → KeyBanc Capital Markets Inc.; Stephens → Stephens Inc.

### Business lines described as lines
- "HVAC division of NSI Industries" (acquired by Lennox International Inc.) and "Industrial businesses of Roper Technologies, Inc." (acquired by Clayton, Dubilier & Rice, LLC) are described as the sale of those lines, as the book describes them. Sponsor acquirer named in full as the book names it.
- The Hisco, Inc acquirer row keeps the book's "Distribution Solutions Group, Inc." rather than "the Company", so the transaction row reads as the book lists it; footnote (5) uses "the Company".

## 5. Terms introduced without a glossary

No `defined_terms.md` / `defined_terms.json` was supplied, so each term is introduced once, in the advisor's own form (the opinion letter's), and used in that form thereafter:

| Term | Introduced as |
| --- | --- |
| Special Committee | "the special committee of the board of directors (the 'Special Committee')" |
| Company | "Distribution Solutions Group, Inc. (the 'Company')" |
| William Blair | "William Blair & Company, L.L.C. ('William Blair')" |
| Merger Sub / Intermediate / Parent | "Eclipse Acquisitions Merger Sub, Inc. ('Merger Sub')", "Eclipse Intermediate Acquisitions, LLC ('Intermediate')", "Eclipse Parent Acquisitions, LLC ('Parent')" |
| Merger Agreement | "the Agreement and Plan of Merger, dated as of July 15, 2026, by and among Parent, Intermediate, Merger Sub and the Company (the 'Merger Agreement')" |
| Merger | "the merger of Merger Sub with and into the Company, with the Company surviving as a wholly owned subsidiary of Intermediate and an indirect wholly owned subsidiary of Parent" |
| Merger Consideration | "$35.00 in cash per share of Company Common Stock, without interest" |
| Company Common Stock | "common stock, par value $1.00 per share, of the Company" |
| SEC | "the Securities and Exchange Commission (the 'SEC')" |
| Forecasts | the letter's label for the fiscal 2026–2030 management forecasts provided July 8, 2026 |
| LTM | "last twelve months ('LTM')" |
| CY 2026E | "calendar year 2026 expected ('CY 2026E')" |

Used but **not** introduced, because the opinion letter itself does not define them and states that capitalized terms not otherwise defined have the meanings ascribed in the Merger Agreement: **Disinterested Stockholders**, **Excluded Shares**. Flagged for the reviewer to confirm the proxy defines both before this section.

Normalisations logged: the book's "Management Plan Forecast" is written throughout as **Forecasts**, the term the annexed opinion letter defines; the book's "Adj. EBITDA" is written as **Adjusted EBITDA** in prose (abbreviated in table headers only); the book's "ECLIPSE" project name is never used.

## 6. `[REVIEWER: ...]` items

None. The fee sentence is complete from `facts.json`, so no `[REVIEWER: fee amount]` marker is carried.

## 7. Known deviation

`length vs base 1.23` — about 23% over the base precedent rather than within 20%. The book presents **eight** core analyses against the base precedent's five, and the section carries the book's full seven-company comps table (six metric columns plus four statistics rows), twelve-transaction table with footnotes, nine-row implied premiums table, three-row premiums-paid percentile table and two 3×3 sensitivity grids. Four rounds of trimming removed roughly 2,700 characters of narrative (items 6, 7, 9 and 10 in §4 above, plus abbreviated table headers); further cuts would have removed rows or parameters the book states.

## 8. Last self-score line

```
SUMMARY  advisor language 0.514 | letter carry-over 0.431 | shell retention 0.506 | book analyses presented 1.0 (missing: none) | glossary terms used 0 (no glossary), written in another form: 0 | peer names with legal suffix 7/7 | numbers not in inputs 0/347 | commentary 0 | markers False | reviewer markers 0 | tables True | length vs base 1.23
```
