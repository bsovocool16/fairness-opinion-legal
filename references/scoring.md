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
| analyses present | every analysis the book shows, presented with a result | 1.00 |
| numbers | per-share ranges and parameters read from the draft against the advisor's disclosed values | 1.00 overlap when stated |
| tables | every peer and precedent row the book lists | 23 of 24 with complete tables; William Blair: 95 of 95 filed table values reproduced |
| proxy defined terms used | share of the glossary terms the filed section uses that the draft uses | 0.59 without a glossary; 0.93 to 0.95 with one (bake-off preview) |
| reviewer grades | parsimony (retained precedent text kept verbatim apart from facts) and justification (every deletion reasoned against the book), 0 to 2 | 1.67 / 1.83 |
| hygiene | commentary, placeholders or markers in the draft | 0 of 24 |

Filed sections are noisy: the filing is edited by several hands after the first draft, so a draft that matches the advisor's
precedents more closely than the filing does is not wrong. Parsimony with reasons is the objective, not string match.
