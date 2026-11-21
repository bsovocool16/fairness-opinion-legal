# What is scored, and the numbers to date

The method was built and tested on 24 held-out deals (board book plus opinion letter in, the section as filed held out) over
seven iterations with GPT-6 as the drafter, and on a bake-off of the two drafting modes. Text metrics compare the draft
with the section as filed; the self-scorer inside the package reports the same signals against the precedents and the
book, so the drafter can score itself before delivery.

| signal | how it is measured | v6 (24 deals, median) |
|---|---|---|
| advisor's own language | share of the draft's 6-word phrases (numbers and names masked) found in the advisor's precedents, the shell or the letter | 0.63 (filed section itself: 0.35) |
| filed section reproduced | share of the filed section's phrases the draft carries | 0.25 |
| letter carried | share of the opinion letter's phrases in the draft | 0.49 |
| paragraphs traceable to a precedent | 60% of a paragraph's phrases found in the advisor's precedents | 0.43 (filed: 0.21) |
| analyses present | every analysis the book shows that the advisor's filed sections present, with a result; an analysis no precedent presents, a reference item carried as a table, or a sensitivity grid counts against the draft (a corpus survey of 729 filed sections found reference-only items filed by most advisors, in a one-sentence form, and by William Blair never) | 1.00 |
| numbers | per-share ranges and parameters read from the draft against the advisor's disclosed values | 1.00 overlap when stated |
| tables | every peer and precedent row the book lists | 23 of 24 with complete tables; William Blair: 95 of 95 filed table values reproduced |
| proxy defined terms used | share of the glossary terms the filed section uses that the draft uses | 0.59 without a glossary; 0.73 (objective) and 0.77 (procedure) with one, 24 deals |
| reviewer grades | parsimony (retained precedent text kept verbatim apart from facts) and justification (every deletion reasoned against the book), 0 to 2 | 1.67 / 1.83 |
| hygiene | commentary, placeholders or markers in the draft | 0 of 24 |

Self-scorer change, November 2026 (0.3.3): the scorer's catch-all for company names now matches legal suffixes in any case
("Acme Holdings, Inc." was left unmasked before, because the suffix list matched only lowercase). Measured on the bundled
Distribution Solutions deal only, since the 24 deals above are not in this repository: advisor's own language 0.635 to 0.651
for the draft and 0.624 to 0.636 for the section as filed; letter carry-over and shell retention moved by less than half a
point. Expect the 0.63 median above to read about 0.64 to 0.65 under the current scorer, more for drafts with long peer tables;
the table keeps the v6 figures as measured.

Filed sections are noisy: the filing is edited by several hands after the first draft, so a draft that matches the advisor's
precedents more closely than the filing does is not wrong. Parsimony with reasons is the objective, not string match.
