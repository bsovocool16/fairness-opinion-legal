# Drafting task: procedure mode

Substitute `<deal dir>` and `<plugin>` before use. Derived from the precedent bank and 24 prior drafts by a review model, adapted to the deal folder.

---

You are drafting the "Opinion of [Advisor]" section of the merger proxy statement for the deal in `<deal dir>`. Read this
procedure, `<plugin>/references/form-notes.md` and `<plugin>/references/checks.md` first. Use only files inside the deal folder
and the plugin's scripts; do not use the network. Inputs: `inputs/book.txt` and `inputs/book_ocr.txt` (the board book, text layer and OCR); `inputs/opinion_letter.txt`;
`facts.json` (deal facts, advisor, regime); `defined_terms.md` and `.json` when a draft proxy was supplied; `inputs/engagement_letter.*`
and `inputs/relationship_memo.*` when supplied (fee terms; the advisor's relationships); `deck_analyses.json` (our reading of the
book); `shell/` (shell_suggested.txt, shell_composite.txt, shell_composite_eligible.txt, rationale.json with the three best bases,
provenance.json); `precedents/` (this advisor's filed sections, INDEX.json with date, form, regime and analyses; any firm_*.txt
shell). Names come from the book and this advisor's other sections; disclosure facts from facts.json, the letter, the engagement
letter and the relationship memo when present. `python3 <plugin>/scripts/selfscore.py <deal dir> <draft>` scores a draft; run it
as part of the checks.

Deliver `draft/section.txt` and `draft/log.md`. The first file must read as filed
text. The second is a separate source and change log. Write both files yourself without asking for confirmation.

Before step 1, read the reviewer's feedback notes that apply (`python3 <plugin>/scripts/feedback.py for <deal dir> --stage draft`):
   corrections from earlier runs, to follow and to list in the log; a note cannot add a fact the inputs lack.

1. Establish the transaction and the source roles. Read the complete opinion letter, the book text and OCR, the facts,
   the proxy glossary and the shell provenance. The signed letter controls recipient, opinion scope, beneficiaries,
   exclusions, date, procedures, consent, qualifications and opinion approval. The book controls the actual analyses,
   selected observations, financial assumptions, dates, units and results. facts.json and the letter control engagement,
   fees, prior or concurrent services and reasons for selection. The glossary controls the spelling and use of proxy terms
   only when the underlying meaning agrees. Precedents control form, never current facts. Where facts.json is a summary,
   prefer the identified primary source for its field; do not average contradictory figures. Record unresolved conflicts
   and source choices in the log.

2. Classify the actual book before selecting the form. Record page, analysis, case or segment, date, source of forecasts,
   core, reference or illustrative status, and whether material is current, superseded or supporting background. Inspect
   substantive content; a table of contents, an assumption disclaimer or the word "DCF" alone does not establish an
   analysis. Check OCR against text where tables are lost. Treat deck_analyses.json and shell markers as aids, not
   conclusions. Distinguish selected market observations from a method actually used to derive value. Inventory every
   table and every named peer and transaction row, including reference and appendix items. Identify missing cells in the log.

3. Select the closest complete same-advisor base by recipient and side, transaction and security type, analysis set,
   forecast cases and length. Check its beginning, ending, tables and advisor identity. Exclude unrelated proxy sections and
   extraction debris. Start from the composite shell when it fits; otherwise choose another ranked base or assemble
   same-advisor paragraphs for the actual analyses. Name the actual base and every borrowed paragraph. A supplied bad splice
   or irrelevant case is not mandatory text. Record the selected unfilled assembly, its paragraph ids, provenance and word
   count before filling. Choose the structure before filling; then preserve the order of retained paragraphs. Place
   reference items and prior presentations where this advisor's precedents put them, without making them core analyses. An
   analysis that none of this advisor's precedents presents is omitted and logged; a reference item appears only in the
   form the precedents use for it, never as a table unless a precedent carries one; a sensitivity grid is never reproduced.
   If there is no usable same-advisor paragraph, use the letter's corresponding language in the third person and log the
   exception. If there is no precedent at all, state that only in the log; do not invent a house style.

4. Build a term map before filling. Keep the book, letter and proxy vocabularies separate: the same word, especially
   Company or Board, can identify different entities in each. An annex-local definition is not automatically a definition
   for the surrounding proxy; prefer the narrative term for the same concept. For each generic or precedent-defined
   expression, identify the same concept in the glossary and use the proxy's term, with its capitalization, throughout its
   scope: once the proxy defines a term, the section uses it every time. Match meaning, not similar words: cash
   consideration, total cash-plus-contingent value, different stock classes, appraisal exclusions and affiliate exclusions
   may differ. Preserve individual forecast versions and cases, preparation and approval dates, and who supplied or
   approved them; do not collapse distinct forecast sets into one label. If the glossary defines the concept, use it
   without a new local definition. If a required concept is absent, use the supported letter or book term and introduce it
   once in the advisor's form. Never invent a proxy section title, annex number or definition. A truncated or conflicting
   glossary entry is unresolved evidence, not authority to change opinion scope. Record the fallback and any new local
   definition in the log.

5. Resolve names separately from terms. Selected companies are named by their full legal names; a precedent transaction
   that was the sale of a business line is described as the sale of that line, as the book describes it; sponsors are
   treated as this advisor's precedents treat them. Do not invent legal suffixes, replace an acquired business with its
   parent, or substitute a current successor for a historical target. A ticker is an identifier, not a display name. If a
   full name cannot be verified from the book, this advisor's other sections or the examples, retain the book label,
   preserve the row and log the gap.

6. Fill, do not rewrite. Keep each retained paragraph verbatim except for supported deal content, proxy terms and names,
   mechanical person, tense and number changes, and evident extraction repairs. Do not paraphrase, merge or reorder
   retained paragraphs to improve prose. Where the letter and the shell cover the same ground, fill the shell's review and
   reliance paragraph from the letter; never append a second version. Preserve the letter's substantive review items,
   approvals, consents, assumptions, limitations and exceptions, in the base's bullet, number or paragraph syntax. Borrow a
   same-advisor module for an uncovered item rather than omit a material qualification. Never carry over a base's oral
   opinion, equal-weighting assertion, no-prior-services claim, fee, forecast case, asset adjustment or fact about the
   transaction merely because it sounds standard.

7. Preserve coverage and every table entry among the analyses this advisor's precedents present. Keep every such analysis,
   and reference items only where and how the precedents present them; omit and log an analysis no precedent presents. Keep every selected-company and transaction row and every supplied
   multiple for those rows, including rows marked NM or NA and group or summary rows. Do not trim rows to meet length.
   Preserve source headers, periods, units, currencies, signs, precision, dates, adjustments and footnotes. Separate
   observed multiples, selected ranges, source metrics, enterprise and equity values and final per-share results. Retain
   each case and the actual denominator. A supporting input panel is not automatically a new valuation method. Do not
   recompute displayed statistics from rounded values or infer missing cells.

8. Complete disclosures from current sources. Preserve supported fee amounts, payment events, contingency, credits,
   reimbursements, indemnities and prior or concurrent relationships in the advisor's form. Do not describe silence as "no
   prior services". Do not infer oral delivery from a written letter. Include earlier-presentation history only from
   supplied dates and materials. If a fact is unavailable after checking the permitted sources, omit the unsupported
   sentence or the smallest unsupported clause and record the missing fact in the log. A missing table cell is not
   permission to omit its row.

9. Account for every shell paragraph and hold the length. The log maps every shell paragraph to a draft location or a
   deletion reason. Permitted deletions: an absent analysis or case, duplicate coverage, an unsupported current factual
   claim, wrong-advisor or non-opinion material, extraction debris. Name the controlling source. Count draft and base
   words by the same whitespace rule, tables included; INDEX.json gives characters, not words. Aim for 80 to 120% of the
   base's word count and report the eligible assembled shell's length as well. If essential source coverage prevents the
   band, choose a better-fitting base or record the exact excess or shortfall and its cause; do not delete facts, rows or
   qualifications to force compliance, and do not pad a short draft. A ratio above 1.4 requires a specific review for
   duplication and unsupported material.

10. Run the checks in `<plugin>/references/checks.md` against the actual files and run the self-scorer on the draft. Confirm the term map, names, opinion scope,
    every source row, cell and footnote, each analysis and status, all shell dispositions, fee arithmetic and timing,
    source conflicts, length and output cleanliness. Record pass, not applicable or unresolved with a locator for each
    check. Do not put the log or verification commentary in the draft.

Output standard: no commentary, drafting notes, placeholders, markers, source-availability statements, model discussion,
checklists or log entries in the section. The log states the model identity as available, the source files used, the base
id, the shell and borrowed-paragraph map, the classifications, the term and name mappings, deletions with reasons,
unresolved inputs, counts and checks. Fidelity to this advisor's language and factual accuracy come first.
