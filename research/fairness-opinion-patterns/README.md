# Fairness-opinion patterns: banker DCF judgment calls in SEC filings, 2001–2026

Dataset and code behind the draft post "The deal price is the answer. The DCF is the work shown."
(`post/fairness-opinion-numbers.html`, a self-contained page). Built from public EDGAR filings and public court opinions
on CourtListener; nothing here is legal or investment advice.

## What is here

| path | what |
|---|---|
| `data/analysis_deal_bank.csv` | 5,136 rows, one per bank DCF per deal (4,172 deals): discount-rate range, perpetuity growth, exit multiple, implied per-share range, compared price, price position in the range, phrase flags, deal type, 10-yr / 30-yr Treasury at filing |
| `data/books_features.csv` | 869 board books (SC 13E3 / SC TO exhibits): bank, risk-free rate and tenor, equity risk premium, beta source flags (Barra, Bloomberg, Duff & Phelps / Kroll), size premium |
| `data/same_deal_pairs.csv` | 270 cash deals where two banks valued the same company on the same date |
| `data/appraisal/` | 44 Delaware appraisal decisions with the court's and both experts' inputs and values (`notes.md` has method and gaps) |
| `data/results.json` | every number and chart series in the post |
| `data/nlp_results.json` | bank-attribution classifier results: accuracy, per-bank recall, signature phrases |
| `scripts/` | the pipeline, in order (below) |

The raw text of every DCF paragraph (`blocks_text.jsonl.gz`, 8 MB) and the EDGAR search index are kept outside the repo, in the
project's shared folder under `fairness-blog/data/`.

## Pipeline

Run from this folder, with `EDGAR_UA` set to your name and email (the SEC requires a contact in every request).

1. `01_index.py`: EDGAR full-text search for DEFM14A, DEFM14C, SC 14D9, SC 13E3 and SC TO-T documents containing a DCF, by year.
2. `02_fetch.py` then `02b_totext.py`: download each document and convert it to text with the plugin's own `html_to_text`.
3. `03_build.py`: run `extract.py` (proxy DCF paragraphs) and `extract_book.py` (board books) over every document.
4. `04_dedup.py`: one DCF per bank per target CIK within 18 months, preferring the definitive proxy.
5. `05_features.py`: market data, deal type, price position, terminal method.
6. `06_nlp.py`: TF-IDF (1–3 grams) + logistic regression naming the bank from its masked DCF paragraph; 5-fold CV and a 2016/2019 time split.
7. `07_books.py`: attribute board books to banks and pick label-adjacent values.
8. `08_results.py`: regressions (rate pass-through, variance decomposition), heaping, court-versus-bank comparisons; writes `results.json`.

The post is `post/src.html` with `results.min.json` inlined.

## Accuracy

A hand check of 30 random deal-bank rows found the discount-rate range right in 30 of 30. Exit multiples (implied multiples
mistaken for inputs) and the compared price (a range endpoint picked up instead of the price) were the weakest fields; both rules
were tightened after the check. Board-book values come from scrambled PDF text layers and are noisy, so the post uses only shares
and medians from them. Deal type is keyword-based. The appraisal set is limited to opinions CourtListener holds.
