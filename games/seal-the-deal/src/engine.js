// Seal the Deal — valuation engine (pure functions, no DOM). Shared by the game and the solver.
// All $ in millions except per-share values.

const DIFF = {
  easy:   { key: 'easy',   label: 'EASY',   sub: 'Summer Analyst', minutes: 540, need: 2, needDcf: false, cushion: 0.1, plausMin: 40, waccBand: 3.0, tgrMax: 4.5, tgrMin: 0.0, sensMax: 1.5, casesLocked: false, minMaxOK: true,  penMult: 1.0, startTime: 22 * 60 },
  medium: { key: 'medium', label: 'MEDIUM', sub: 'First-Year Analyst', minutes: 360, need: 2, needDcf: true,  cushion: 0.3, plausMin: 55, waccBand: 2.0, tgrMax: 3.75, tgrMin: 0.5, sensMax: 1.0, casesLocked: false, minMaxOK: true,  penMult: 1.25,  startTime: 25 * 60 },
  hard:   { key: 'hard',   label: 'HARD',   sub: 'Third-Year (Up for Associate)', minutes: 300, need: 3, needDcf: true,  cushion: 0.3, plausMin: 60, waccBand: 1.25, tgrMax: 3.25, tgrMin: 1.0, sensMax: 0.75, casesLocked: true,  minMaxOK: false, penMult: 1.5,  startTime: 26 * 60 },
};

// Minutes each kind of action costs on the clock.
const COST = { wacc: 15, tgr: 15, sens: 15, case: 60, sbc: 30, adj: 20, peer: 15, prec: 15, bridge: 30, range: 30, special: 45 };

const DEALS = [
  {
    id: 'jrky', name: 'Gristle & Sons', ticker: 'JRKY', sector: 'Packaged Meat Snacks',
    side: 'sell', counterparty: 'Cinderblock Capital Partners',
    headline: 'Take-private by a sponsor at a 7.9% DISCOUNT to the stock price.',
    memo: 'The founders are rolling their equity and getting board seats. Public holders get $14.00 cash. Stock closed at $15.20. Make the offer fair to the public holders.',
    offer: 14.00, price: 15.20, w52: [13.10, 18.40],
    shares: 60, netDebt: 400,
    ltmRev: 900, ltmMargin: 0.150, sbcPct: 0.010, sbcDefault: 'cash',
    da: 0.030, capex: 0.035, nwc: 0.10, tax: 0.25,
    wacc: 8.0, tgr: 2.5,
    cases: {
      base:     { label: 'Management Base', growth: [0.045, 0.045, 0.040, 0.040, 0.035], margin: [0.145, 0.150, 0.152, 0.155, 0.155] },
      upside:   { label: 'Management Upside', growth: [0.07, 0.07, 0.06, 0.06, 0.05], margin: [0.15, 0.16, 0.17, 0.175, 0.18] },
      downside: { label: '"Sensitivity Case"', growth: [0.01, 0.01, 0.015, 0.02, 0.02], margin: [0.135, 0.132, 0.130, 0.130, 0.130] },
    },
    adjustments: [
      { name: 'Plant closure costs (one-time)', amt: 9, on: true, pen: 4, note: 'genuinely one-time' },
      { name: 'Jerky recall (third "one-time" recall)', amt: 7, on: true, pen: 0, note: 'happens every year' },
      { name: 'Founder\'s jet (personal use)', amt: 5, on: true, pen: 2, note: 'arguably personal' },
    ],
    peers: [
      { name: 'Beefcake Brands', mult: 13.5, pen: 3, tag: 'growthy' },
      { name: 'Hormone-Free Holdings', mult: 12.6, pen: 5, tag: 'closest comp' },
      { name: 'Salt Lick Snacks', mult: 11.4, pen: 6, tag: 'closest comp' },
      { name: 'PorkBelly Partners', mult: 10.9, pen: 4, tag: '' },
      { name: 'Generic Protein Co.', mult: 9.8, pen: 3, tag: '' },
      { name: 'Sad Pretzel Inc.', mult: 8.6, pen: 6, tag: 'different category' },
      { name: 'Distressed Dried Fruit', mult: 7.2, pen: 12, tag: 'in Chapter 11' },
    ],
    peersDefault: [true, true, true, true, true, false, false],
    precedents: [
      { name: 'Snackzilla / Kraftwerk (2021)', mult: 14.2, pen: 3 },
      { name: 'Meaty Bits / Sponsor X (2022)', mult: 12.5, pen: 5 },
      { name: 'Crunch Corp / BigFoods (2023)', mult: 11.1, pen: 5 },
      { name: 'Jerky Joe / Sponsor Y (2019)', mult: 10.0, pen: 3 },
      { name: 'Expired Snacks / Liquidator (2009)', mult: 6.5, pen: 10 },
      { name: 'Stale Chips / Vulture LP (2020)', mult: 7.0, pen: 9 },
    ],
    precDefault: [true, true, true, true, false, false],
    bridge: [
      { name: 'Treat operating leases as debt', amt: 140, on: false, pen: 3 },
      { name: 'Deduct unfunded pension', amt: 60, on: false, pen: 2 },
      { name: 'Count "trapped" overseas cash as zero', amt: 50, on: false, pen: 6 },
    ],
    special: { name: 'Apply "execution risk" haircut (-10% EBITDA)', pen: 10, kind: 'haircut' },
  },
  {
    id: 'vapr', name: 'VaporLoop AI', ticker: 'VAPR', sector: 'Generative AI "Platform"',
    side: 'buy', counterparty: 'Synergex Holdings (our client, the buyer)',
    headline: 'Our client is paying a 47% premium for a company with 4% EBITDA margins.',
    memo: 'Synergex\'s CEO saw a demo and fell in love. Synergex shareholders need to hear the $44.00/share price is fair to THEM. Stock was $30.00 last week. Make the price fair to the buyer.',
    offer: 44.00, price: 30.00, w52: [19.50, 36.80],
    shares: 100, netDebt: -300,
    ltmRev: 600, ltmMargin: 0.04, sbcPct: 0.16, sbcDefault: 'cash',
    da: 0.04, capex: 0.05, nwc: 0.05, tax: 0.21,
    wacc: 11.0, tgr: 3.0,
    cases: {
      base:     { label: 'Management Base', growth: [0.30, 0.26, 0.22, 0.18, 0.15], margin: [0.06, 0.09, 0.12, 0.15, 0.18] },
      upside:   { label: '"AGI Case"', growth: [0.45, 0.40, 0.35, 0.30, 0.25], margin: [0.08, 0.13, 0.18, 0.22, 0.25] },
      downside: { label: 'Street Case', growth: [0.20, 0.16, 0.13, 0.10, 0.08], margin: [0.04, 0.06, 0.08, 0.10, 0.11] },
    },
    adjustments: [
      { name: 'GPU "investment" (expensed)', amt: 0, on: false, pen: 9, add: 30, note: 'they rent GPUs. It is opex.' },
      { name: 'Pre-revenue "AGI Lab"', amt: 0, on: false, pen: 7, add: 18, note: 'run-rate burn, forever' },
      { name: 'Severance (laid off half the AGI Lab)', amt: 0, on: false, pen: 2, add: 6, note: 'plausibly one-time' },
    ],
    peers: [
      { name: 'Hypescale', mult: 62, pen: 9, tag: 'meme stock' },
      { name: 'Prompt Industries', mult: 48, pen: 3, tag: '' },
      { name: 'TokenWorks', mult: 41, pen: 5, tag: 'closest comp' },
      { name: 'Legacy Software Co.', mult: 18, pen: 4, tag: 'closest comp' },
      { name: 'ERP Dinosaur Inc.', mult: 14, pen: 3, tag: '' },
      { name: 'IT Consulting Group', mult: 11, pen: 2, tag: 'body shop' },
    ],
    peersDefault: [false, true, true, true, true, true],
    precedents: [
      { name: 'ChatNest / MegaCloud (2024)', mult: 95, pen: 10 },
      { name: 'Neural Pets / Toyco (2025)', mult: 70, pen: 8 },
      { name: 'DataLake / Oracular Inc. (2022)', mult: 32, pen: 5 },
      { name: 'CRM Thing / Software PE (2023)', mult: 22, pen: 5 },
      { name: 'Helpdesk Co. / Sponsor (2024)', mult: 17, pen: 4 },
    ],
    precDefault: [false, false, true, true, true],
    bridge: [
      { name: 'Ignore convertible notes due 2027', amt: -250, on: false, pen: 7 },
      { name: 'Count customer prepayments as cash', amt: -120, on: false, pen: 5 },
    ],
    special: { name: 'Include synergies ($30m run-rate, Day 1)', pen: 14, kind: 'synergy', amt: 30 },
  },
  {
    id: 'pllt', name: 'Pallet Ventures', ticker: 'PLLT', sector: 'Third-Party Logistics',
    side: 'sell', counterparty: 'The Pallet Family Trust (owns 58%)',
    headline: 'Controlling shareholder squeeze-out, $22.00 vs. $24.10 stock price.',
    memo: 'The family controls the board, the special committee, and the holiday party. They want the minority out at $22.00. Management\'s projections are... sunny. Make the offer fair to the unaffiliated holders.',
    offer: 22.00, price: 24.10, w52: [18.90, 27.50],
    shares: 80, netDebt: 600,
    ltmRev: 2400, ltmMargin: 0.105, sbcPct: 0.006, sbcDefault: 'cash',
    da: 0.025, capex: 0.03, nwc: 0.08, tax: 0.25,
    wacc: 9.0, tgr: 2.5,
    cases: {
      base:     { label: 'Management Base', growth: [0.08, 0.08, 0.07, 0.06, 0.05], margin: [0.110, 0.115, 0.120, 0.125, 0.130] },
      upside:   { label: 'Board Retreat Case', growth: [0.12, 0.12, 0.10, 0.09, 0.08], margin: [0.12, 0.13, 0.14, 0.145, 0.15] },
      downside: { label: '"Freight Recession" Case', growth: [0.01, 0.02, 0.03, 0.03, 0.03], margin: [0.10, 0.10, 0.10, 0.10, 0.10] },
    },
    adjustments: [
      { name: 'Truck fleet impairment', amt: 18, on: true, pen: 5, note: 'non-cash, real' },
      { name: 'Tariff "disruption" costs', amt: 14, on: true, pen: 1, note: 'every quarter since 2018' },
      { name: 'Family members\' consulting fees', amt: 8, on: true, pen: 0, note: 'yikes' },
    ],
    peers: [
      { name: 'FastFreight Global', mult: 12.8, pen: 5, tag: 'closest comp' },
      { name: 'Dock Dynamics', mult: 11.5, pen: 6, tag: 'closest comp' },
      { name: 'Conveyor Belt Corp.', mult: 10.6, pen: 4, tag: '' },
      { name: 'LastMile Ltd.', mult: 10.0, pen: 3, tag: '' },
      { name: 'Regional Trucking Co.', mult: 8.4, pen: 2, tag: 'asset-heavy' },
      { name: 'Shipping Container Lessor', mult: 7.1, pen: 7, tag: 'different business' },
      { name: 'Pony Express Holdings', mult: 6.0, pen: 10, tag: 'founded 1860' },
    ],
    peersDefault: [true, true, true, true, true, false, false],
    precedents: [
      { name: 'CargoWave / Sponsor (2022)', mult: 13.1, pen: 4 },
      { name: 'BoxHaul / Megacarrier (2021)', mult: 12.0, pen: 4 },
      { name: 'Freightly / Strategic (2023)', mult: 10.4, pen: 5 },
      { name: 'Load Co. / Sponsor (2019)', mult: 9.2, pen: 3 },
      { name: 'Mellow Freight / Creditors (2023)', mult: 5.5, pen: 10 },
    ],
    precDefault: [true, true, true, true, false],
    bridge: [
      { name: 'Treat operating leases as debt', amt: 220, on: false, pen: 3 },
      { name: 'Deduct self-insurance reserves', amt: 90, on: false, pen: 3 },
      { name: 'Deduct "contingent" tariff refund', amt: 70, on: false, pen: 7 },
    ],
    special: { name: 'Apply "execution risk" haircut (-10% EBITDA)', pen: 10, kind: 'haircut' },
  },
  {
    id: 'dial', name: 'DialTone Legacy Networks', ticker: 'DIAL', sector: 'Copper Landlines',
    side: 'buy', counterparty: 'Ostrich Telecom (our client, the buyer)',
    headline: 'Paying 9.5x EBITDA for a business shrinking 6% a year.',
    memo: 'Ostrich\'s CEO is "betting on the landline comeback." The price is $31.00 per DIAL share (stock was $21.40). Ostrich holders need to hear that this is fair to them. Revenue has declined every year since the flip phone.',
    offer: 31.00, price: 21.40, w52: [17.20, 23.90],
    shares: 150, netDebt: 4200,
    ltmRev: 4000, ltmMargin: 0.30, sbcPct: 0.005, sbcDefault: 'cash',
    da: 0.12, capex: 0.11, nwc: 0.02, tax: 0.25,
    wacc: 8.0, tgr: -1.0,
    cases: {
      base:     { label: 'Management Base', growth: [-0.05, -0.05, -0.04, -0.04, -0.03], margin: [0.30, 0.30, 0.295, 0.29, 0.29] },
      upside:   { label: '"Landline Renaissance" Case', growth: [0.00, 0.01, 0.02, 0.02, 0.02], margin: [0.31, 0.32, 0.33, 0.33, 0.33] },
      downside: { label: 'Reality', growth: [-0.08, -0.08, -0.08, -0.08, -0.08], margin: [0.29, 0.28, 0.27, 0.26, 0.25] },
    },
    adjustments: [
      { name: 'Copper theft remediation', amt: 0, on: false, pen: 5, add: 70, note: 'monthly' },
      { name: 'Payphone decommissioning', amt: 0, on: false, pen: 3, add: 45, note: 'since 2004' },
      { name: 'Union settlement (one-time)', amt: 0, on: false, pen: 1, add: 30, note: 'genuinely one-time' },
    ],
    peers: [
      { name: 'Fiber Future Inc.', mult: 11.5, pen: 7, tag: 'growing fiber' },
      { name: 'TowerCo REIT', mult: 19.0, pen: 12, tag: 'not a telco' },
      { name: 'CableBox Corp.', mult: 7.8, pen: 4, tag: 'closest comp' },
      { name: 'Rural Lines Co.', mult: 6.2, pen: 5, tag: 'closest comp' },
      { name: 'Fax Machine Holdings', mult: 5.1, pen: 3, tag: '' },
      { name: 'Pager Networks', mult: 4.3, pen: 2, tag: '' },
    ],
    peersDefault: [false, false, true, true, true, true],
    precedents: [
      { name: 'Bell Spinco / Sponsor (2007)', mult: 11.0, pen: 9, },
      { name: 'Copper Corp. / Telco (2006)', mult: 10.2, pen: 9 },
      { name: 'RuralNet / Infra Fund (2021)', mult: 7.6, pen: 5 },
      { name: 'Wireline Co. / PE (2022)', mult: 6.4, pen: 5 },
      { name: 'Dial-Up ISP / Liquidation (2015)', mult: 4.0, pen: 2 },
    ],
    precDefault: [false, false, true, true, true],
    bridge: [
      { name: 'Exclude unfunded pension ($600m)', amt: -600, on: false, pen: 8 },
      { name: 'Exclude asbestos reserves', amt: -250, on: false, pen: 6 },
      { name: 'Value spectrum licenses at 2021 prices', amt: -400, on: false, pen: 7 },
    ],
    special: { name: 'Include synergies ($150m run-rate, Day 1)', pen: 14, kind: 'synergy', amt: 150 },
  },
  {
    id: 'zzzz', name: 'Sleepwell DTC', ticker: 'ZZZZ', sector: 'Direct-to-Consumer Mattresses',
    side: 'sell', counterparty: 'Bedrock Holdings (with the CEO rolling 100%)',
    headline: 'Management buyout at $6.50; the CEO keeps his equity, his jet, and his job.',
    memo: 'The CEO is on both sides. Bedrock offers $6.50 cash; stock is $7.40 and the CEO\'s own projections say the business is turning around. Make $6.50 fair to the public holders. The plaintiffs\' bar is already reading the proxy.',
    offer: 6.50, price: 7.40, w52: [5.10, 9.95],
    shares: 220, netDebt: 150,
    ltmRev: 1500, ltmMargin: 0.10, sbcPct: 0.04, sbcDefault: 'addback',
    da: 0.03, capex: 0.025, nwc: 0.04, tax: 0.25,
    wacc: 10.5, tgr: 2.5,
    cases: {
      base:     { label: 'Management Base', growth: [0.08, 0.10, 0.10, 0.09, 0.08], margin: [0.11, 0.12, 0.13, 0.14, 0.15] },
      upside:   { label: 'CEO Keynote Case', growth: [0.15, 0.15, 0.14, 0.12, 0.10], margin: [0.12, 0.14, 0.16, 0.17, 0.18] },
      downside: { label: '"Sleepless" Case', growth: [0.02, 0.03, 0.03, 0.03, 0.03], margin: [0.095, 0.095, 0.10, 0.10, 0.10] },
    },
    adjustments: [
      { name: 'Influencer "brand investment"', amt: 25, on: true, pen: 0, note: 'it is marketing' },
      { name: 'Returns from 100-night trial', amt: 18, on: true, pen: 2, note: 'it is the business model' },
      { name: 'Warehouse fire (insured)', amt: 10, on: true, pen: 5, note: 'actually one-time' },
    ],
    peers: [
      { name: 'Cozy Digital', mult: 14.0, pen: 4, tag: '' },
      { name: 'PillowTalk Brands', mult: 12.2, pen: 6, tag: 'closest comp' },
      { name: 'Bed-in-a-Box Global', mult: 11.0, pen: 6, tag: 'closest comp' },
      { name: 'Furniture Superstore', mult: 9.0, pen: 3, tag: '' },
      { name: 'Department Store Co.', mult: 6.5, pen: 6, tag: 'different business' },
      { name: 'Waterbed Wholesale', mult: 5.0, pen: 10, tag: 'peak was 1987' },
    ],
    peersDefault: [true, true, true, true, false, false],
    precedents: [
      { name: 'Snoozely / Sponsor (2021)', mult: 15.5, pen: 3 },
      { name: 'Comfort Corp. / Strategic (2022)', mult: 12.0, pen: 5 },
      { name: 'RestEasy / Sponsor (2023)', mult: 10.5, pen: 5 },
      { name: 'Linens Plus / PE (2019)', mult: 8.8, pen: 3 },
      { name: 'Futon Universe / Creditors (2020)', mult: 5.5, pen: 10 },
    ],
    precDefault: [true, true, true, true, false],
    bridge: [
      { name: 'Treat operating leases as debt', amt: 180, on: false, pen: 3 },
      { name: 'Deduct customer warranty reserve', amt: 90, on: false, pen: 4 },
      { name: 'Include out-of-the-money options', amt: 0, shares: 18, on: false, pen: 6 },
    ],
    special: { name: 'Apply "execution risk" haircut (-10% EBITDA)', pen: 10, kind: 'haircut' },
  },
];

function initialState(deal, diff) {
  return {
    wacc: deal.wacc, tgr: deal.tgr, sens: 0.5, case: 'base', sbc: deal.sbcDefault,
    adj: deal.adjustments.map(a => a.on),
    peers: deal.peersDefault.slice(), prec: deal.precDefault.slice(),
    bridge: deal.bridge.map(b => b.on),
    compsRange: 'iqr', precRange: 'iqr', special: false,
  };
}

function pctile(xs, q) {
  const s = xs.slice().sort((a, b) => a - b);
  if (!s.length) return 0;
  const i = (s.length - 1) * q, lo = Math.floor(i), hi = Math.ceil(i);
  return s[lo] + (s[hi] - s[lo]) * (i - lo);
}

function projections(deal, st) {
  const c = deal.cases[st.case];
  const rows = [];
  let rev = deal.ltmRev;
  const syn = deal.special.kind === 'synergy' && st.special ? deal.special.amt : 0;
  for (let t = 0; t < 5; t++) {
    const prev = rev;
    rev = rev * (1 + c.growth[t]);
    let ebitda = rev * c.margin[t];
    if (deal.special.kind === 'haircut' && st.special && t > 0) ebitda *= 0.9;
    ebitda += syn;
    const sbc = rev * deal.sbcPct;
    if (st.sbc === 'addback') ebitda += sbc;
    const dna = rev * deal.da;
    const ebit = ebitda - dna;
    const tax = Math.max(0, ebit) * deal.tax;
    const capex = rev * deal.capex;
    const dnwc = (rev - prev) * deal.nwc;
    const fcf = ebitda - tax - capex - dnwc;
    rows.push({ rev, ebitda, sbc, dna, ebit, tax, capex, dnwc, fcf, growth: c.growth[t] });
  }
  return rows;
}

function bridgeAmt(deal, st) {
  let debt = deal.netDebt, shares = deal.shares;
  deal.bridge.forEach((b, i) => { if (st.bridge[i]) { debt += b.amt || 0; shares += b.shares || 0; } });
  return { debt, shares };
}

function adjTotal(deal, st) {
  let s = 0;
  deal.adjustments.forEach((a, i) => { if (st.adj[i]) s += (a.add != null ? a.add : a.amt); });
  return s;
}

function ltmEbitda(deal, st) {
  // Reported LTM EBITDA (after SBC) + toggled adjustments (+ SBC if added back)
  let e = deal.ltmRev * deal.ltmMargin;
  // For adjustments that start "on", reported figure already excludes them: reported = adjusted - on adjustments.
  e += adjTotal(deal, st);
  if (st.sbc === 'addback') e += deal.ltmRev * deal.sbcPct;
  if (deal.special.kind === 'synergy' && st.special) e += deal.special.amt;
  return e;
}

function ntmEbitda(deal, st) {
  const p = projections(deal, st)[0];
  return p.ebitda + adjTotal(deal, st);
}

function dcfPerShare(deal, st, wacc, g) {
  const rows = projections(deal, st);
  const w = wacc / 100, gg = g / 100;
  if (w - gg < 0.01) return NaN;
  let pv = 0;
  rows.forEach((r, t) => { pv += r.fcf / Math.pow(1 + w, t + 0.5); });
  const tv = rows[4].fcf * (1 + gg) / (w - gg);
  const pvtv = tv / Math.pow(1 + w, 4.5);
  const ev = pv + pvtv;
  const { debt, shares } = bridgeAmt(deal, st);
  return { ps: (ev - debt) / shares, ev, pv, pvtv, tvShare: pvtv / ev };
}

function ranges(deal, st) {
  const { debt, shares } = bridgeAmt(deal, st);
  const lo = dcfPerShare(deal, st, st.wacc + st.sens, st.tgr - 0.25);
  const hi = dcfPerShare(deal, st, st.wacc - st.sens, st.tgr + 0.25);
  const mid = dcfPerShare(deal, st, st.wacc, st.tgr);
  const pm = deal.peers.filter((p, i) => st.peers[i]).map(p => p.mult);
  const qm = deal.precedents.filter((p, i) => st.prec[i]).map(p => p.mult);
  const cq = st.compsRange === 'minmax' ? [0, 1] : [0.25, 0.75];
  const pq = st.precRange === 'minmax' ? [0, 1] : [0.25, 0.75];
  const ntm = ntmEbitda(deal, st), ltm = ltmEbitda(deal, st);
  const ps = (m, e) => (m * e - debt) / shares;
  const cm = [pctile(pm, cq[0]), pctile(pm, cq[1])];
  const qmm = [pctile(qm, pq[0]), pctile(qm, pq[1])];
  return {
    dcf: [lo.ps, hi.ps], dcfMid: mid.ps, tvShare: mid.tvShare,
    comps: [ps(cm[0], ntm), ps(cm[1], ntm)], compsMult: cm,
    prec: [ps(qmm[0], ltm), ps(qmm[1], ltm)], precMult: qmm,
    ntm, ltm, debt, shares,
  };
}

function plausibility(deal, st, diff) {
  const items = [];
  const add = (pen, text) => { if (pen > 0.01) items.push({ pen, text }); };
  const dw = Math.abs(st.wacc - deal.wacc);
  add(Math.max(0, dw - 0.5) / 0.25 * 5, `WACC ${st.wacc.toFixed(2)}% vs. CAPM ${deal.wacc.toFixed(2)}%`);
  if (st.tgr > 3.0) add((st.tgr - 3.0) / 0.25 * 6, `Perpetual growth ${st.tgr.toFixed(2)}% beats long-run GDP`);
  const tgrFloor = Math.min(1.5, deal.tgr - 0.5);
  if (st.tgr < tgrFloor) add((tgrFloor - st.tgr) / 0.25 * 4, `Perpetual growth ${st.tgr.toFixed(2)}% is gloomier than the company's own outlook`);
  if (st.sens > 0.5) add((st.sens - 0.5) / 0.25 * 6, `WACC sensitivity of ±${st.sens.toFixed(2)}% (street is ±0.50%)`);
  if (st.case === 'upside') add(15, `Used the ${deal.cases.upside.label} nobody approved`);
  if (st.case === 'downside') add(12, `Swapped in your own ${deal.cases.downside.label}`);
  if (st.sbc !== deal.sbcDefault && st.sbc === 'addback') add(14, 'Treated stock comp as free money');
  deal.adjustments.forEach((a, i) => { if (st.adj[i] !== a.on) add(a.pen, `${st.adj[i] ? 'Added back' : 'Removed'}: ${a.name}`); });
  deal.peers.forEach((p, i) => { if (st.peers[i] !== deal.peersDefault[i]) add(p.pen, `${st.peers[i] ? 'Added' : 'Dropped'} peer ${p.name}${p.tag ? ' (' + p.tag + ')' : ''}`); });
  const np = st.peers.filter(Boolean).length;
  if (np < 4) add(15, `Only ${np} peers left in the comp set`);
  deal.precedents.forEach((p, i) => { if (st.prec[i] !== deal.precDefault[i]) add(p.pen, `${st.prec[i] ? 'Added' : 'Dropped'} precedent ${p.name}`); });
  const nq = st.prec.filter(Boolean).length;
  if (nq < 3) add(15, `Only ${nq} precedents left`);
  deal.bridge.forEach((b, i) => { if (st.bridge[i] !== b.on) add(b.pen, b.name); });
  if (st.compsRange === 'minmax') add(10, 'Comps range is min-to-max, not interquartile');
  if (st.precRange === 'minmax') add(10, 'Precedents range is min-to-max, not interquartile');
  if (st.special) add(deal.special.pen, deal.special.name);
  const r = ranges(deal, st);
  if (r.tvShare > 0.80) add((r.tvShare - 0.80) * 100, `Terminal value is ${(r.tvShare * 100).toFixed(0)}% of the DCF`);
  const total = items.reduce((s, x) => s + x.pen, 0) * diff.penMult;
  items.forEach(x => x.pen *= diff.penMult);
  items.sort((a, b) => b.pen - a.pen);
  return { score: Math.max(0, Math.round(100 - total)), items };
}

// The "committee line": how far into each bar the offer has to sit. 0 = anywhere in or past the bar.
function line(deal, r, diff) {
  const lo = Math.min(r[0], r[1]), hi = Math.max(r[0], r[1]), c = diff.cushion || 0;
  return deal.side === 'sell' ? lo + c * (hi - lo) : hi - c * (hi - lo);
}
function supports(deal, rng, diff) {
  const f = (r) => (deal.side === 'sell' ? deal.offer >= line(deal, r, diff) - 1e-9 : deal.offer <= line(deal, r, diff) + 1e-9);
  return { dcf: f(rng.dcf), comps: f(rng.comps), prec: f(rng.prec) };
}

function verdict(deal, st, diff) {
  const rng = ranges(deal, st);
  const sup = supports(deal, rng, diff);
  const n = (sup.dcf ? 1 : 0) + (sup.comps ? 1 : 0) + (sup.prec ? 1 : 0);
  const pl = plausibility(deal, st, diff);
  const methodsOk = n >= diff.need && (!diff.needDcf || sup.dcf);
  return { rng, sup, n, pl, methodsOk, plausOk: pl.score >= diff.plausMin, fair: methodsOk && pl.score >= diff.plausMin };
}

// "Gap" — how far the offer sits from being supported, summed over methods needed (for the boss's mood and the solver)
function gap(deal, st, diff) {
  const v = verdict(deal, st, diff);
  const g = ['dcf', 'comps', 'prec'].map(k => {
    const L = line(deal, v.rng[k], diff);
    const d = deal.side === 'sell' ? (L - deal.offer) : (deal.offer - L);
    return { k, d: Math.max(0, d / deal.offer) };
  });
  let need = g.slice();
  if (diff.needDcf) { const dcf = need.shift(); need.sort((a, b) => a.d - b.d); need = [dcf].concat(need.slice(0, diff.need - 1)); }
  else { need.sort((a, b) => a.d - b.d); need = need.slice(0, diff.need); }
  return need.reduce((s, x) => s + x.d, 0);
}

// Every move available, as {kind, key, apply(st)->st|null, cost}
function moves(deal, st, diff) {
  const out = [];
  const clone = () => JSON.parse(JSON.stringify(st));
  const step = (field, delta, lo, hi, kind) => {
    const v = Math.round((st[field] + delta) * 100) / 100;
    if (v < lo - 1e-9 || v > hi + 1e-9) return;
    const n = clone(); n[field] = v; out.push({ kind, act: `${field}:${delta}`, label: `${field} ${delta > 0 ? '+' : ''}${delta}`, st: n, cost: COST[kind] });
  };
  step('wacc', 0.25, 0, deal.wacc + diff.waccBand, 'wacc');
  step('wacc', -0.25, deal.wacc - diff.waccBand, 99, 'wacc');
  step('tgr', 0.25, -99, diff.tgrMax, 'tgr');
  step('tgr', -0.25, Math.min(diff.tgrMin, deal.tgr - 1), 99, 'tgr');
  step('sens', 0.25, 0, diff.sensMax, 'sens');
  step('sens', -0.25, 0.25, 99, 'sens');
  if (!diff.casesLocked) ['base', 'upside', 'downside'].forEach(c => { if (c !== st.case) { const n = clone(); n.case = c; out.push({ kind: 'case', act: 'case:' + c, label: 'case ' + c, st: n, cost: COST.case }); } });
  { const n = clone(); n.sbc = st.sbc === 'cash' ? 'addback' : 'cash'; out.push({ kind: 'sbc', act: 'sbc:' + n.sbc, label: 'sbc ' + n.sbc, st: n, cost: COST.sbc }); }
  const tog = (arr, kind, minOn) => st[arr].forEach((v, i) => {
    const n = clone(); n[arr][i] = !v;
    if (minOn && n[arr].filter(Boolean).length < minOn) return;
    out.push({ kind, act: `${kind}:${i}`, label: `${arr}[${i}] ${!v}`, st: n, cost: COST[kind] });
  });
  tog('adj', 'adj'); tog('peers', 'peer', 3); tog('prec', 'prec', 3); tog('bridge', 'bridge');
  if (diff.minMaxOK) ['compsRange', 'precRange'].forEach(f => { const n = clone(); n[f] = st[f] === 'iqr' ? 'minmax' : 'iqr'; out.push({ kind: 'range', act: 'range:' + f, label: f + ' ' + n[f], st: n, cost: COST.range }); });
  { const n = clone(); n.special = !st.special; out.push({ kind: 'special', act: 'special:x', label: 'special ' + n.special, st: n, cost: COST.special }); }
  return out;
}

if (typeof module !== 'undefined') module.exports = { line, DIFF, COST, DEALS, initialState, projections, ranges, plausibility, verdict, gap, moves, dcfPerShare, ltmEbitda, ntmEbitda, bridgeAmt, adjTotal, pctile };
