# Drafting task: objective mode

Substitute `<deal dir>` and `<plugin>` before use. The drafter reads this and nothing else about how to work.

---

Produce the "Opinion of [Advisor]" section of the merger proxy statement for the deal in `<deal dir>` from the inputs in
that folder. Use only files inside it and the plugin's scripts; do not use the network; write the files yourself.

Inputs
- `inputs/book.txt` and, if present, `inputs/book_ocr.txt`: the advisor's board book (text layer and OCR); `inputs/opinion_letter.txt`:
  the opinion letter (or `facts.json` says it is pending); `facts.json`: the deal facts, the advisor, the regime; `deck_analyses.json`:
  our reading of the analyses the book presents; `defined_terms.md` and `.json` when a draft proxy was supplied: the proxy's defined
  terms with the sentence defining each; `inputs/engagement_letter.*` and `inputs/relationship_memo.*` when supplied: the fee terms
  and the advisor's relationships (not public; use them for the fees and relationships paragraphs).
- `precedents/`: this advisor's filed sections for other deals of the same regime where possible (`INDEX.json`: date, form, regime,
  analyses presented, coverage of this book), plus any `firm_*.txt` shell the firm supplied.
- `shell/`: the base precedent (`shell_suggested.txt`), a composite assembled from the approved precedents for this book
  (`shell_composite.txt`, with `[[NOT IN THIS BOOK]]` and `[[BORROWED FROM ...]]` markers), the ranking (`rationale.json`) and
  provenance. Use them or not.
- The reviewer's feedback notes that apply to this deal and stage: `python3 <plugin>/scripts/feedback.py for <deal dir> --stage draft`.
  They are corrections from earlier runs; follow them and list in the log which you applied. A note cannot add a fact the inputs lack.
- `python3 <plugin>/scripts/selfscore.py <deal dir> <draft>` scores a draft against everything here. Run it as often as you like.

Output
- `draft/section.txt`: the section as it would be filed (plain text or markdown; tables as | rows |).
- `draft/log.md`: the feedback notes applied; the precedent(s) built from; what was deleted or added and why; facts not available and omitted; terms introduced
  without a glossary; the last self-score line; `[REVIEWER: ...]` items with the paragraph they concern.

Scoring
The draft is later placed beside the section the company files, and the reviewer grades it before that, on:
1. how much of the draft is this advisor's own filed language (6-word phrases, numbers and names masked, found in the precedents,
   the shell or the letter): this is the first-ranked signal; the self-scorer reports it as advisor_language_share, and drafts
   built by filling a precedent reach about 0.6 or more, while added tables, reference paragraphs and re-phrased review lists
   count as new language unless they come from a precedent;
2. whether every analysis in the book that this advisor's filed sections present is presented with its results, with the numbers,
   peers, transactions and parameters the book shows, and every row the book lists; the section presents what this advisor files:
   an analysis in the book that none of the precedents presents is not presented but listed in the log for the reviewer
   (`shell/rationale.json` names them); a reference item, such as a 52-week range or analyst price targets, appears only in the
   form the precedents use for it, typically a sentence in an "Other Factors" paragraph, never as a table unless a precedent
   carries one (`rationale.json` quotes the form); a sensitivity grid is never reproduced, the section states the resulting
   range as the precedents do;
3. defined terms: once the proxy defines a term, the section uses that term every time; without a glossary, each term is introduced
   once in the advisor's form and listed in the log;
4. names: selected companies by full legal name; a precedent that was the sale of a business line described as the sale of that
   line; sponsors as this advisor's precedents treat them;
5. the reviewer's grades of parsimony (retained precedent text kept verbatim apart from the deal facts) and of the log's
   justification of every deletion and addition against the book;
6. no commentary, drafting notes, placeholders or markers in the section; a fact the inputs lack is omitted and logged, never
   invented (in particular no "no prior relationships" without the relationship memo; a fee sentence that cannot be completed
   carries exactly `[REVIEWER: fee amount]`); length within about 20% of the base precedent.
The self-scorer reports 1 (against the precedents), 2 (coverage of the analyses the precedents present, analyses outside them
that the draft presents, reference items carried as tables, sensitivity grids), 3, 4 and 6.
