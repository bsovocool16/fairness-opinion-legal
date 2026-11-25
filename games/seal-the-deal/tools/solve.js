// Balance checker: for each deal × difficulty, beam-search the cheapest path to FAIR.
const E = require('../src/engine.js');
const f = (x) => (isFinite(x) ? x.toFixed(2) : 'NaN');
const only = process.argv[2];

function key(st) { return JSON.stringify(st); }
function score(deal, st, diff, spent) {
  const v = E.verdict(deal, st, diff);
  const g = E.gap(deal, st, diff);
  const plShort = Math.max(0, diff.plausMin - v.pl.score);
  return g * 400 + plShort * 1.5 + spent / 60;
}

function solve(deal, diff) {
  let beam = [{ st: E.initialState(deal, diff), spent: 0, path: [] }];
  const seen = new Map();
  let best = null;
  for (let depth = 0; depth < 40; depth++) {
    const next = [];
    for (const node of beam) {
      for (const m of E.moves(deal, node.st, diff)) {
        const spent = node.spent + m.cost;
        if (spent > diff.minutes) continue;
        const k = key(m.st);
        if (seen.has(k) && seen.get(k) <= spent) continue;
        seen.set(k, spent);
        const n = { st: m.st, spent, path: node.path.concat(m.label) };
        const v = E.verdict(deal, m.st, diff);
        if (v.fair) { if (!best || spent < best.spent || (spent === best.spent && v.pl.score > best.pl)) best = { ...n, pl: v.pl.score }; continue; }
        n.s = score(deal, m.st, diff, spent);
        next.push(n);
      }
    }
    next.sort((a, b) => a.s - b.s);
    beam = next.slice(0, 200);
    if (!beam.length) break;
  }
  return best;
}

for (const deal of E.DEALS) {
  if (only && deal.id !== only) continue;
  const st0 = E.initialState(deal, E.DIFF.easy);
  const r = E.ranges(deal, st0);
  console.log(`\n== ${deal.name} (${deal.side}) offer ${deal.offer} px ${deal.price}`);
  console.log(`  DCF ${f(r.dcf[0])}-${f(r.dcf[1])} mid ${f(r.dcfMid)} TV% ${(r.tvShare * 100).toFixed(0)} | comps ${f(r.comps[0])}-${f(r.comps[1])} (${r.compsMult.map(x => x.toFixed(1)).join('-')}x NTM ${r.ntm.toFixed(0)}) | prec ${f(r.prec[0])}-${f(r.prec[1])} (LTM ${r.ltm.toFixed(0)})`);
  for (const dk of ['easy', 'medium', 'hard']) {
    const diff = E.DIFF[dk];
    const b = solve(deal, diff);
    if (!b) { console.log(`  ${dk}: UNSOLVABLE`); continue; }
    const v = E.verdict(deal, b.st, diff);
    console.log(`  ${dk}: ${b.spent}/${diff.minutes} min, plaus ${b.pl}/${diff.plausMin}, n=${v.n}  [${b.path.join(', ')}]`);
  }
}
