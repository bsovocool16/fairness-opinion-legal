# Seal the Deal

A satirical pixel-art browser game. You are an investment banking analyst. Each deal arrives with a bad price, and you have until the 7:00 AM board call to get the Fairness Committee to sign off that it is "fair, from a financial point of view."

**Play:** open `dist/seal-the-deal.html` in any browser. One file, no install. (Fonts load from Google Fonts when online and fall back to monospace offline.)

## How it plays

- Five made-up deals: three sell-side (push value down to meet a lowball offer) and two buy-side (push value up to justify an overpayment).
- A football field shows DCF, trading comps and precedent ranges against the offer. On medium and hard the offer has to clear a gold "committee line" inside each bar.
- Levers: WACC, terminal growth, WACC sensitivity (bar width), projection case, SBC treatment, EBITDA add-backs, peer and precedent selection, min–max vs. interquartile ranges, equity-bridge items, plus a synergies or "execution risk haircut" button. Each move costs clock time.
- The Smell Test (plausibility) drops as you deviate from defensible defaults. The committee rejects anything below the bar, and a kick-back costs 30 minutes.
- Run out of time and the MD signs it himself. It is always fair.
- The MD's pixel face gets angrier with the gap to fair and the clock; his look gets more disheveled across the night (tie drops, jacket comes off, stubble, finally the tie goes around his head).

| | Easy | Medium | Hard |
|---|---|---|---|
| Clock | 9 h | 6 h | 5 h |
| Methods needed | 2 of 3 | 2 of 3 incl. DCF | 3 of 3 |
| Committee line | 10% into bar | 30% | 30% |
| Smell test min | 40 | 55 | 60 |
| Other | all levers | tighter WACC/TGR caps | cases locked, interquartile only, ±1.25% WACC band |

## Layout

- `src/engine.js` — pure valuation engine and deal data (DCF, comps, precedents, bridge, plausibility, committee verdict). Runs in node too.
- `src/game.js`, `src/style.css`, `src/index.html` — UI, pixel boss and desk rendering.
- `tools/build.js` — inlines everything into `dist/seal-the-deal.html` (standalone) and `dist/artifact.html` (no document skeleton).
- `tools/solve.js` — beam-search balance checker: cheapest path to FAIR per deal and difficulty.
- `tools/playtest.js`, `tools/fullrun.js` — Playwright smoke tests (screenshots, full five-deal runs with a greedy bot).

```
node tools/build.js && node tools/solve.js && node tools/fullrun.js /tmp
```

All companies, deals and people are fictional.
