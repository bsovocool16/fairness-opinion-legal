// Plays a whole run in the real page for each difficulty using a greedy agent; reports outcomes + errors.
const { chromium } = require('playwright');
const out = process.argv[2] || '.';
(async () => {
  const b = await chromium.launch();
  const errs = [];
  for (const diff of ['easy', 'medium', 'hard']) {
    const p = await b.newPage({ viewport: { width: 1280, height: 900 } });
    p.on('pageerror', (e) => errs.push(diff + ' ' + e.message));
    await p.goto('file://' + __dirname + '/../dist/seal-the-deal.html');
    await p.click(`[data-diff="${diff}"]`);
    for (let i = 0; i < 5; i++) {
      await p.click('#m-go');
      const log = await p.evaluate(() => {
        const s = window.__std, G = s.G, deal = DEALS[G.dealIdx], d = DIFF[G.diff];
        const acts = [];
        for (let k = 0; k < 40 && !G.over; k++) {
          const v = verdict(deal, G.st, d);
          if (v.fair) break;
          // greedy: best single move by gap + plausibility shortfall
          let best = null, bs = Infinity;
          for (const m of moves(deal, G.st, d)) {
            const vv = verdict(deal, m.st, d);
            const sc = gap(deal, m.st, d) * 400 + Math.max(0, d.plausMin - vv.pl.score) * 1.5 + m.cost / 60;
            if (sc < bs) { bs = sc; best = m; }
          }
          s.handle(best.act); acts.push(best.act);
        }
        return { acts, fair: verdict(deal, G.st, d).fair, spent: G.spent };
      });
      if (!(await p.isVisible('#modal'))) await p.click('#btn-submit');
      await p.waitForTimeout(150);
      const h2 = await p.textContent('#modal-inner h2');
      console.log(diff, i + 1, h2, '| spent', log.spent, '| moves', log.acts.length);
      if (h2.includes('KICKED')) { await p.click('#m-ok'); await p.evaluate(() => window.__std.G.spent = 9999); await p.evaluate(() => window.__std.handle('wacc:0.25')); }
      if (i === 4 && diff === 'medium') await p.screenshot({ path: out + '/10-letter.png' });
      await p.click('#m-next');
    }
    await p.waitForTimeout(200);
    console.log(diff, 'FINALE:', (await p.textContent('#modal-inner')).replace(/\s+/g, ' ').slice(0, 300));
    if (diff === 'hard') await p.screenshot({ path: out + '/11-finale.png' });
    await p.close();
  }
  console.log('errors', errs);
  await b.close();
})();
