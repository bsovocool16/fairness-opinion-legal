---
name: proxy-glossary
description: >
  Optional: build the deal's defined-terms glossary from a draft proxy statement
  or the merger agreement so the section uses the proxy's terms from the start
  (Merger, Merger Consideration, Company Common Stock, Special Committee,
  Projections). Use when a draft proxy or the agreement exists, when the user
  says "defined terms", "glossary", "use the proxy's terms", or after intake
  supplied a draft proxy.
argument-hint: "[deal code] [<proxy or agreement file>]"
---

# /proxy-glossary

1. Take the file from `$ARGUMENTS` or `inputs/draft_proxy.*`. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/defined_terms.py <file> <deal dir>`. It writes `defined_terms.json` and `defined_terms.md`: each term with the sentence that defines it.
2. Show the count and the first fifteen terms. Flag scope traps the drafter must watch: two stock classes, several forecast versions, an annex-local "Company" that differs from the proxy's.

## Why it is optional

The usual drafter starts before the proxy exists. Without a glossary the section introduces its own terms in the advisor's form and the reviewer conforms them later; with one, the draft uses the proxy's terms from the first pass. On the test set the glossary raised the share of the proxy's terms used from 0.59 to 0.9 and above.

## What it does NOT do

- It does not pick terms for the drafter; scope (which stock class, which forecast set) is a judgment the drafter records in the log.
