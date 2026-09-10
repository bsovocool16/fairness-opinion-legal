# The two drafting modes

**objective** (default). The task states the objective, the inputs and what is scored, and nothing about how to work. The
drafter reads the advisor's precedents and the worked examples, builds from the shell or from precedents of its own choice,
and scores itself with the self-scorer as often as it likes. This is the setting the owner prefers on principle: set inputs and
outputs, let the scoring drive the learning, avoid a rulebook.

**procedure**. A ten-step procedure derived by a review of the precedent bank and 24 prior drafts (establish the source
roles; classify the book; select the base; build a term map; resolve names; fill, do not rewrite; preserve coverage and every
table entry; complete disclosures from current sources; account for every shell paragraph and hold the length; run the
checks), with a form note per advisor and a pre-delivery checklist.

Bake-off on the full 24 test deals (Sep 2026, GPT-6 drafter): objective mode beat the procedure on the reviewer's
parsimony grade (1.54 against 1.38), defined-term use (1.83 against 1.54), names (2.00 on every deal against 1.33), and
hygiene (no commentary, no contradicted deletions); the procedure edged filed recall by three points, a number tainted by
the fact that the procedure was derived from a review that had read the filings. Both modes raised proxy-term use from
0.59 to above 0.7 and both wrote more new material than the prior version, mostly added tables and reference analyses.
Objective mode is the default. The profile picks the mode; `task-objective.md` and `task-procedure.md` hold the texts.

## Which model drafts

Port test on one deal (William Blair, 13e-3), objective mode, one pass each, scored against the filing: Claude Fable and
Claude Opus reproduced the filing as well as the GPT-6 reference run (filed recall 0.77 and 0.73 against 0.73) and named every
peer by full legal name; Claude Sonnet kept the numbers and tables but rewrote more (filed recall 0.62). Token use was the same
across models (about 300k a deal, most of it reading the book and the precedents), so Opus is the efficient default drafter;
use Fable for an unusual deal. Extraction and review passes run on Haiku; search, shell, scoring and redline are scripts.
