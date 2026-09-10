# fairness-opinion-legal practice profile

<!-- This file is the TEMPLATE. The cold-start interview writes the completed profile to
     ~/.claude/plugins/config/fairness-opinion-legal/CLAUDE.md, and every skill reads that copy.
     [PLACEHOLDER] marks a value the interview fills in; [DEFAULT] marks a working default the user accepted. -->

## Who's using this

- Name: [PLACEHOLDER]
- Role: [PLACEHOLDER] (associate | senior associate | partner | in-house counsel | paralegal | other)
- Practice setting: [PLACEHOLDER] (law firm | in-house | bank legal | other)
- Firm or company: [PLACEHOLDER]
- Who reviews before anything leaves the building: [PLACEHOLDER]

## EDGAR identity

The SEC asks every automated client to identify itself with a contact. Precedent search sends this as its User-Agent.

- Contact for SEC requests: [PLACEHOLDER: name and email, e.g. "Jane Roe jane.roe@firm.com"]
- Request pace: [DEFAULT: 0.5 seconds between requests]

## Precedent defaults

- Look-back window: [DEFAULT: 6 years]. Older filings only when the advisor has fewer than five sections in the window.
- Forms searched: [DEFAULT: DEFM14A, DEFM14C, SC 14D9, SC 13E3]
- Precedents returned per deal: [DEFAULT: 8, ranked by regime match, coverage of the book's analyses, then recency]
- Firm shell library (optional): [PLACEHOLDER: path to a folder of the firm's own shells by advisor, or "none"]

## Drafting

- Regime: asked at intake for every deal (Rule 13e-3 going-private, or conventional). Never inferred silently.
- Drafting mode: [DEFAULT: "objective" — the drafter gets the inputs, the scoring and the self-scorer, nothing about how to work]. Alternative: "procedure" (a ten-step derived procedure with a form note and checklist). See `references/drafting-modes.md`.
- Drafter model: [DEFAULT: "opus" — the tested default drafter]. Alternative: "fable" (the top model; for an unusual deal; costs more). Read by `pipeline`, `section-draft` and `demo --live`; `--model` on a command overrides it for one run.
- Names: selected companies by full legal name; a precedent that was the sale of a business line described as the sale of that line; sponsors as the advisor's precedents treat them.
- Defined terms: once the proxy defines a term, the section uses it every time. A glossary from the draft proxy is optional (`/fairness-opinion-legal:proxy-glossary`); without one the drafter introduces terms itself and flags them for the reviewer.
- House style notes: [PLACEHOLDER: anything the firm does differently from the advisor's precedents, or "follow the advisor's precedents"]

## Outputs

- Work-product header on every document: [DEFAULT: "DRAFT — ATTORNEY WORK PRODUCT — FOR REVIEW — NOT FOR FILING"]
- Formats: [DEFAULT: clean draft as .docx and .txt; redline as .docx and .pdf; drafting log as .md]
- Redline convention: [DEFAULT: Litera-style — blue double underline added, red strikethrough deleted, green moved, change bars]

## Gates

A gate is a point where the skill stops and waits for the user before continuing.

- After intake: confirm the regime, the deal facts and the analyses read from the book. [DEFAULT: on]
- After precedent search: approve the precedent set, add or remove filings. [DEFAULT: on]
- After the shell: review the shell before markup. [DEFAULT: off — the redline shows every change anyway]
- Before delivery: the reviewer named above signs off. [DEFAULT: on]

## Deals

- Deals folder: `~/.claude/plugins/config/fairness-opinion-legal/deals/`
- Active deal: none

## Available integrations

- EDGAR full-text search and document fetch over HTTPS: required, no connector.
- Document conversion: `pdftotext` (poppler) for board books, `pandoc` or python-docx for Word files, LibreOffice for PDF output. Missing tools degrade to text-only outputs; the skill says so rather than failing silently.
- OCR for image-only board books: optional (`ocrmypdf` or `tesseract`); without it the skill reports which pages have no text layer.
