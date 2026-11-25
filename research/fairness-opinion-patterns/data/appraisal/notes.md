# Delaware appraisal (8 Del. C. § 262) DCF dataset: notes

Files in this folder:
- `appraisal_cases.csv`: one row per decision (44 rows), without the quote fields.
- `appraisal_cases.json`: the same rows plus `key_quote` and `key_quote_position`.

## 1. Scope and counts

- **44 decision records** covering **39 distinct case families**.
- 35 are Court of Chancery (`delch`) decisions, 8 are Delaware Supreme Court (`del`) decisions, and 1 row combines Chancery 1997 with its Supreme Court affirmance in 1999 (MPM).
  - Paired Chancery and Supreme Court rows exist for Dell, DFC, Golden Telecom, Aruba and Jarden.
  - Gilbert v. MPM (Ch. 1997) and its Supreme Court affirmance (1999) share one row.
- Dates run from 1991 (Radiology Assocs.) to 2026-08-07 (Gladstone v. EBC Holdings / Firebrand).
- **Inclusion rule:** a statutory appraisal, or a combined appraisal and entire-fairness case, where the court computed, adopted, adjusted or explicitly evaluated a DCF (or a single-stage capitalized-cash-flow / discounted-net-income model).
  - Cases where the court rejected the DCF in favour of the deal price or market price are kept. They are tagged in `valuation_method_relied_on`, because that rejection is itself the post-2017 pattern.
- **Excluded after checking:**
  - Metromedia Int'l (2009): preferred-stock contract value, no DCF.
  - Paskill v. Alcoma (Del. 2000): net asset value.
  - Ramadurgam v. Destiny XYZ (2026): § 155 fractional-share case, not § 262.
  - Ban v. Manheim (2025): fiduciary damages.
  - Endeavor (2025): a lead-counsel ruling.
  - Huff v. CKx (Del. 2015): a 2,000-character order with no valuation text.
  - Hauppauge (2022): a § 220 books-and-records case.

### Field conventions
- Percentages are plain numbers: `6.18` means 6.18%.
- Blank (CSV) or `null` (JSON) means the opinion does not state the value. Nothing was imputed.
- `court_wacc` is the discount rate the court actually applied. For all-equity or bank (equity-level) models it equals the cost of equity, and `notes` says so (Dunmire, ONTI, Firebrand, Delaware Open MRI, Union Illinois).
- `fv_pct_of_deal` = court fair value ÷ deal price × 100. It is computed only when both are numeric per-share values.
- Supreme Court rows that reverse and remand (Dell 2017, DFC 2017) carry no fair value of their own.
- `confidence`:
  - **high**: every populated number was located in the opinion text with `search_document` or `read_document`.
  - **medium**: some inputs are inherited from an adopted expert model or table, or there is an interpretive caveat (described in `notes`).
- `key_quote_position` is the character offset in CourtListener's `html_with_citations` text, as reported by `search_document`. A few positions are approximate chunk offsets and are marked "approx".

## 2. Method

1. **Source.** Every value comes from the CourtListener MCP tools only:
   - `search` (keyword and semantic) to find candidates;
   - `search_document` to grep for figures, using strings such as "equity risk premium", "WACC", "per share", "perpetuity growth", "beta", "size premium", "discount rate", "terminal", "I adopt", "fair value of";
   - `read_document` to read the surrounding chunks.
   Direct calls to the CourtListener REST API from bash were not reachable.
2. **Extraction.** For each candidate I read the opening chunk (headline values: deal price, the parties' positions, the fair value). I then grepped for and read the cost-of-capital and terminal-value sections, and recorded only figures the court itself states.
3. **Expert figures** are each side's final position as the court reports it. "Petitioner" means the dissenting stockholders' expert. In combined fiduciary cases, it means the minority's expert.
4. **Search queries used** (court filter `delch` / `del`), among others:
   - `appraisal AND "weighted average cost of capital" AND "262"`
   - `"equity risk premium"` (delch)
   - `"capital asset pricing model" appraisal`
   - `"discounted cash flow" "section 262" "fair value"`
   - `caseName:appraisal`
   - semantic queries such as "Delaware appraisal fair value discounted cash flow WACC equity risk premium"
   - caseName OR-lists of known appraisal captions (Dell, DFC, Aruba, Jarden, Solera, Panera, Stillwater, Columbia, Norcraft, AOL, PetSmart, SWS, Clearwire, LPS, BMC, Ancestry, Regal, HFF, Pivotal, Orchard, Cogent, Towerview, Sunbelt, Trilithic, Hintmann, Just Care, Andaloro, Crescent/Mach)
   - `"ISN Software" appraisal`
   - follow-ups on cases cited inside opinions that were already collected (for example, Pivotal's size-premium string cite and Dunmire's ERP string cite).

## 3. Coverage gaps (why this is not exhaustive)

- **Mid-era Chancery opinions available only on Westlaw.** CourtListener does not have these as § 262 merits opinions, so they are missing although they are core DCF precedents:
  - Technicolor (Ch. 1990, 2003/2004)
  - Emerging Communications (2004)
  - Prescott Group v. Coleman (2004)
  - Henke v. Trilithic (2005)
  - Andaloro v. PFPC (2005 merits)
  - U.S. Cellular (2005)
  - Doft v. Travelocity (2004)
  - Sunbelt Beverage (2010)
  - Hanover Direct (2010)
  - Gearreald v. Just Care (2012)
  - Orchard (2012 appraisal)
  - IQ Holdings / ACL (2013)
  - 3M Cogent (2013)
  - Towerview v. Cox Radio (2013)
  - Huff v. CKx (Ch. 2013/2014)
  - Laidler v. Hesco (2014; only a ~10k-character letter is on CL)
  - Le Beau (Ch. 1998)
  - Gholl v. eMachines (Ch. 2004)
  - Crescent/Mach I v. Dr Pepper (Ch. 2007)
  - Gonsalves v. Straight Arrow (Ch.)
  - Hintmann v. Fred Weber (1998)
  - Cede v. JRC (2004)
  - ISN Software (Ch. 2016)
  - Several of these are cited inside collected opinions (for example, Dunmire cites 3M Cogent ERP 5.20, IQ Holdings 5.5 and Orchard 5.2). Those figures were **not** entered as rows because they were not verified in the cited opinion itself.
- **Older opinions are image-heavy.** Some Caselaw Access Project texts replace the DCF tables with "[[Image here]]" (Radiology, ONTI, Delaware Open MRI). Some court inputs, such as the final terminal growth, are therefore missing.
- **Supreme Court affirmances often omit inputs.** Montgomery Cellular and MPM do not restate the court's final WACC, so those inputs are null.
- **Partial extraction.** Some per-share expert values or betas are noted as "not extracted" where the time budget did not allow a full read (Owen v. Cannon respondent value, FairX petitioner value, Delaware Open MRI expert per-share values).

## 4. Pattern summary

### 4.1 Cost of capital inputs adopted by the court

**ERP (court-adopted, 2010+, n = 11)**
- Range 5.97–6.22, median 6.18.
- Values: 5.97, 6.0, 6.03, 6.11, 6.11, 6.18, 6.18, 6.18, 6.21, 6.21, 6.22.
- Every post-2010 court ERP is a Duff & Phelps / Kroll **supply-side** figure or the Golden Telecom 6.0 (supply-side). No post-2010 court in the sample adopted an Ibbotson historical ERP, an implied ERP or a survey ERP.
- Explicit statements:
  - Golden Telecom (2010) leaned supply-side, saying the professional community and not the court should develop the approach.
  - SWS (2017) called supply-side "essentially the default method".
  - Dunmire (2016) took supply-side 6.18 over historical 6.96 and rejected the Duke CFO-survey ERP of 3.55. It observed a 5–7% range in recent appraisal decisions.
  - HFF (2022) said the court "has endorsed" supply-side.
  - In Firebrand (2026) both experts kept the Kroll supply-side 6.22 even though the Damodaran implied ERP was raised.
  - In Stillwater (2019), petitioner's expert used a Damodaran implied ERP of 5.34. The court did not reach the DCF.
- Pre-2010 decisions used historical premia: ONTI 8.4 over a T-bill; Radiology 13.5 small-cap historical; Delaware Open MRI 7.20 in a build-up.

**Risk-free rate**
- Post-2010 the court used the 20-year Treasury throughout (2.14–3.68).
- ONTI (1999) used a 90-day T-bill.

**Beta**
- Court betas range 0.7 (Dunmire, unlevered bank-industry median) to 2.47 (DFC, smoothed Bloomberg peer beta relevered).
- Approaches seen:
  - blends of raw Bloomberg and industry betas (Golden Telecom: 2/3 Bloomberg raw + 1/3 industry);
  - peer medians relevered with Hamada (DFC, Norcraft, SourceHOV);
  - D&P industry betas (Dunmire).
- Methodological rulings:
  - Dunmire: match the beta type (OLS vs. sum) to the size-premium type; use an unlevered beta for a debt-free company.
  - HFF: choosing a beta with attention to standard errors is supported by Damodaran and Pratt & Grabowski.
  - Union Illinois: an implied beta of 0.3 for a troubled bank is unrealistic.

**Size premium**
- Applied in most court CAPM builds: Ancestry 1.73, DFC 3.52, SWS 3.46, Norcraft 2.69, Jarden 0.57, Dunmire 3.87, SourceHOV 2.68, Firebrand 4.8, and Gesoff (5.33 / 2.41 by subsidiary).
- Rejected or excluded in LPS and in Pivotal (2023). Pivotal cited Damodaran's "Where is the beef?" critique: the proponent bears the burden of proving the factual basis.
- Merlin/AutoInfo (2015) and Gearreald refuse to shave the size premium below the company's actual size decile.
- Company-specific risk premia are consistently disfavoured:
  - Delaware Open MRI calls them "the device experts employ to bring their final results into line with their clients' objectives";
  - Gesoff rejected them;
  - ONTI halved one;
  - Synapse rejected a 40% venture-capital "probability of failure" rate.

**WACC / discount rate**
- Court-applied rates 2010+ (n = 15): range 6.94–17.57, median 10.72.
- Public large and mid caps cluster at **9.5–11.6**: Dell 9.46, LPS 9.56, BMC 10.5, Norcraft 10.60, Ancestry 10.71, DFC 10.72, Clearwire 10.92-equivalent, SourceHOV 11.6.
- Outliers on the low side:
  - Jarden 6.94; the court noted it was below every banker's figure.
  - Pivotal 7.69.
- Small or private companies sit at 11–18: Dunmire 11.07, Synapse 12.0, Owen 14.13, Firebrand 16.51, AutoInfo 17.57. Pre-2010 private-company build-ups reach 18–19 (ONTI 18.35, Radiology 18.14, Delaware Open MRI 18.64).

**Terminal growth**
- Court-adopted (2010+, n = 16): range 2.0–5.0, median 3.1.
- Values cluster at **3.0–3.5**: 3.0 ×3, 3.1 ×3, 3.25, 3.35 ×2, 3.4, 3.5 ×2.
- Outliers:
  - Golden Telecom 5.0 (Russia, nominal);
  - Dell 2.0;
  - Firebrand 2.0, tied to reinvestment consistency;
  - Pivotal 2.5, which split the difference and rejected a 0% "convergence" approach.
- DFC (Del. 2017) reversed the Chancery court's mid-stream move from 3.1% to 4.0%.
- Owen and Dunmire endorse a premium of about 100 bp over inflation.
- The Gordon growth model is used almost universally. Exit-multiple terminal values were criticized or rejected (Synapse, Columbia, ONTI) except in MPM (1997).

**Petitioner vs. respondent gaps**
- Petitioner experts typically used lower WACCs and higher growth. Examples (petitioner vs. respondent):
  - WACC: PetSmart 7.75 vs. 6.35; Clearwire 10.22 vs. 12.44 APV; Jarden 7.88 vs. 7.38; Dunmire 9.51 vs. 13.0.
  - Growth: 4.375 vs. 3.0 (Dunmire); 5 vs. 0 (Pivotal); 4.5 (Clearwire); 3.0 vs. 2.0 (Firebrand).
- Headline expert values often differ by 2–3x.

### 4.2 The shift toward market evidence after DFC (Aug 2017) and Dell (Dec 2017)

**Pre-DFC/Dell (24 records, 22 with fair value as % of deal)**
- Median **109%** of deal price, range 43–271%.
- DCF was the primary method in most cases.
- Large above-deal awards came in controller squeeze-outs and private companies:
  - Radiology 271%, Montgomery Cellular 242%, M.G. Bancorp 207%, Delaware Open MRI 205%, Owen 160%, Gesoff 136%, Dell (Ch.) 128%.
- Arm's-length auctions already produced deal-price awards: Union Illinois 2004, AutoInfo, Ramtron, Ancestry, BMC, LPS, PetSmart.

**Post-DFC/Dell (20 records, 15 with fair value as % of deal)**
- Median **97%** of deal price, range 53–103%. **No post-2017 award exceeds the deal price by more than 3%.**
- Methods relied on:
  - deal price or deal-price-less-synergies: Solera, Aruba (Del.), Columbia, Stillwater, Panera, Regal, HFF, FairX;
  - unaffected trading price: Aruba (Ch.), Jarden;
  - DCF only where market evidence was missing or flawed: AOL, Norcraft, SourceHOV, Synapse, Firebrand, Pivotal half-weight.
- Even where DCF was used, outcomes stayed near the deal price (AOL 97%, Norcraft 103%).
- Several below-deal awards: Clearwire 43%, Synapse 53%, Aruba (Ch.) 69%, Aruba (Del.) 77%, Jarden 82%, HFF 95%, Panera 96%, Solera 97%, AOL 97%. Pre-2017, SWS 92% and Highfields 81% are the earlier below-deal examples.
- Regal (103%) and HFF moved value between signing and closing, through the Tax Act and post-signing performance respectively. This "fair value at closing" adjustment is new after 2020.
- Pivotal (2023/24) held that MFW protections do **not** require deference to the deal price in controller squeeze-outs. It blended comparable companies and DCF to reach $15.44 against a $15 deal price.

### 4.3 Criticism of banker / fairness-opinion DCFs

- **Jarden (2019):** a footnote notes the court's 6.94% WACC was below the Goldman, Deutsche Bank, RBC and Barclays figures.
- **PetSmart (2017):** JPMorgan's "double digit" WACC and its Barra beta came under criticism.
- **Columbia (2019):** the petitioner's 3.0% growth was set against Lazard's 1.4–1.9% and Goldman's 1–2%; terminal value was about 125% of total value.
- **Clearwire (2017):** Centerview used growth of 1–3%.
- **Panera (2020):** Morgan Stanley's "80+% of your value is in the terminus".
- **Regal (2021):** buyer-side advisor DCFs varied with the projection set ($25.70 vs. $36.40).
- **Gesoff (2006):** a fairness-opinion bank was "plainly loyal" to the controller.
- **Montgomery Cellular (2005):** testimony on the source of the merger-price multiple was found false.
- **HFF (2022):** Morgan Stanley's DCF ignored the deal pipeline.
- **Pivotal (2023):** cited the fairness adviser's growth range as support for its own 2.5%.

### 4.4 Surprising or noteworthy findings

- **ERP convergence.** Across 16 years of Chancery decisions the court-adopted ERP never left a 25-basis-point band (5.97–6.22). Discount-rate disputes moved to beta, size premium and capital structure.
- **Discount rates are low relative to banker practice.** Jarden's 6.94% WACC sits below every banker; PetSmart's respondent expert used 6.35%.
- **Size-premium skepticism is recent.** Pivotal (2023) rejected the size premium outright. Earlier cases applied it as "de rigueur" (Delaware Open MRI) or as integral to both experts' models (Dunmire).
- **Law of the case can override finance.** In Technicolor (Del. 2005), the 1991 discount rate of 15.28% displaced a recomputed 19.89%, which moved the value from $21.98 to $28.41.
- **Corrected opinions change headline numbers.** Pivotal's March 2024 corrected opinion raised fair value from $14.83 (below the deal price) to $15.44 (above it). Both versions are on CourtListener: op 9555735 is the original and op 9950150 the corrected version, which is the one used here.
- **Typographical error in ONTI.** ONTI's summary table prints an 18.85% discount rate, but its components sum to 18.35%, which is the rate actually used.

## 5. Caveats for downstream NLP/ML use

- n is small and selection is driven by what CourtListener holds. The pre-2010 period is under-represented and skewed toward private and controller cases.
- The pre- vs. post-2017 comparison is descriptive, not causal.
- Some rows mix equity-level discount rates (banks, all-equity build-ups) with enterprise WACCs. Filter on `notes` or `court_cost_of_equity == court_wacc` before pooling.
- Text offsets refer to CourtListener's `html_with_citations` rendering and can shift if CourtListener re-processes the text.
