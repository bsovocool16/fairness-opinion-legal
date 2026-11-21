# Tests

One command from the repository root:

```
make deps     # once: pytest, hypothesis, the Python packages the scripts use, and the Word renderer's npm package
make test     # everything (about 1.5 minutes); CI runs the same on every push and pull request
make quick    # unit + golden only, a few seconds
```

No network, no model calls, and nothing in your real `~/.claude` is read or written: every script runs with `HOME` pointed at
a scratch folder.

## What is checked

| folder | what | how |
|---|---|---|
| `unit/` | each script's logic: the analysis vocabulary, advisor names, regime, EDGAR table cleanup, section cutting, shell segmentation and splicing, the self-score metrics, feedback scopes, precedent ranking (EDGAR faked), the redline diff | plain examples, one file per script |
| `golden/` | every deterministic stage run in order on the bundled Distribution Solutions deal, each output compared with `golden/expected/<stage>/`; the .docx deliverables checked by structure (header, blue/red marks, word counts in the legend); outputs identical under two hash seeds | snapshots |
| `fuzz/` | properties that must hold for any input: EDGAR figures split over cells come back whole; the redline never loses or invents a word; parsers never crash; and a matrix of every stage on a deal folder with one input missing, empty, binary, truncated or the wrong JSON shape | Hypothesis, fixed seed in CI |

## When a golden fails

A golden failure prints a unified diff of what changed. If the change is intended (you changed the shell builder, the scorer,
the redline), run `make golden-update` and review the rewritten files in `git diff` before committing; the diff is the
record of how the outputs moved.

## Adding a pipeline stage

Stages are declared once in `stages.py`: the command, and the files it writes in the deal folder. Add an entry, run
`make golden-update`, review the new folder under `golden/expected/`. A stage that needs the network or a model belongs
outside the golden run; give it a fake the way `unit/test_precedent_ranking.py` fakes EDGAR, and snapshot what comes after it.

## Fuzzing harder

`make fuzz-deep` runs the properties with 3,000 random examples each and a fresh seed. A failure prints the smallest input
that breaks the property; paste it into an `@example(...)` or a unit test so it stays fixed.

## Known findings (marked xfail)

Tests marked `xfail(strict=True)` document behavior the suite found that was left for a decision rather than changed. Each
reason starts with `FINDING:`. When one is fixed, the test starts passing, pytest reports it, and the marker comes off.
