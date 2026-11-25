/* Seal the Deal — game layer. Depends on engine.js globals. */
(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const money = (x) => (isFinite(x) ? (x < 0 ? '-$' + Math.abs(x).toFixed(2) : '$' + x.toFixed(2)) : 'n/m');
  const mm = (x) => (x < 0 ? '(' + Math.abs(Math.round(x)).toLocaleString() + ')' : Math.round(x).toLocaleString());
  const pct = (x, d = 1) => (x * 100).toFixed(d) + '%';
  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
  const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
  const YEARS = ['FY27E', 'FY28E', 'FY29E', 'FY30E', 'FY31E'];

  // ---------- storage (best scores; optional) ----------
  const store = {
    get(k) { try { return JSON.parse(localStorage.getItem('std:' + k)); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem('std:' + k, JSON.stringify(v)); } catch (e) { /* ignore */ } },
  };

  // ---------- sound ----------
  let actx = null, muted = !!store.get('muted');
  function tone(freq, dur, type = 'square', vol = 0.05, slide = 0) {
    if (muted) return;
    try {
      actx = actx || new (window.AudioContext || window.webkitAudioContext)();
      const o = actx.createOscillator(), g = actx.createGain();
      o.type = type; o.frequency.value = freq;
      if (slide) o.frequency.linearRampToValueAtTime(freq + slide, actx.currentTime + dur);
      g.gain.value = vol; g.gain.exponentialRampToValueAtTime(0.0001, actx.currentTime + dur);
      o.connect(g); g.connect(actx.destination); o.start(); o.stop(actx.currentTime + dur);
    } catch (e) { /* no audio */ }
  }
  const sfx = {
    click: () => tone(660, 0.05),
    tick: () => tone(330, 0.04, 'triangle', 0.04),
    stamp: () => { tone(90, 0.25, 'sawtooth', 0.12, -50); setTimeout(() => tone(60, 0.2, 'square', 0.08), 60); },
    bad: () => { tone(160, 0.18, 'sawtooth', 0.07); setTimeout(() => tone(110, 0.3, 'sawtooth', 0.07), 160); },
    note: () => { tone(880, 0.07, 'square', 0.04); setTimeout(() => tone(1175, 0.09, 'square', 0.04), 80); },
    win: () => [523, 659, 784, 1047].forEach((f, i) => setTimeout(() => tone(f, 0.12, 'square', 0.05), i * 110)),
  };

  // ---------- game state ----------
  let G = null;
  function newRun(diffKey) {
    return { diff: diffKey, dealIdx: 0, dishevel: 0, results: [], ...dealState(0) };
  }
  function dealState(i) {
    const deal = DEALS[i];
    return { st: initialState(deal), spent: 0, rejections: 0, coffee: 0, events: [0.3, 0.62], usedEvents: [], tab: 'memo', over: false, axis: null, actions: 0 };
  }
  const D = () => DIFF[G.diff];
  const DEAL = () => DEALS[G.dealIdx];

  // ---------- boss lines ----------
  const LINES = {
    intro: [
      'Board call is at 7. The deck says FAIR. Your job is to make the math agree with the deck.',
      'Client\'s happy, we\'re happy, the success fee is happy. Get it to fair.',
      'I already told the CEO it\'s fair. Don\'t make me a liar.',
    ],
    wacc: ['Size premium. Company-specific risk premium. Put a premium on the premium.', 'Beta is a feeling, not a number.', 'Who picked that risk-free rate? Pick another one.', 'Use the Duff & Phelps... no, the OTHER one.'],
    waccDown: ['Lower WACC? Sure, the market loves this company. It\'s basically a bond.', 'Debt is cheap if you don\'t look at the rate.'],
    tgr: ['Grows forever. Like my disappointment in you.', 'Perpetuity growth is a vibe.', 'Inflation\'s back, right? Bump it.'],
    tgrDown: ['Low perpetuity growth. Conservative! Nobody ever got sued for being conservative. Probably.'],
    sens: ['Widen the range. If the bar is wide enough, everything is inside it.', 'A range is just a point that believes in itself.'],
    case: ['A different case? Management will "approve" anything at 3 AM.', 'New projections. Same company. Different destiny.'],
    sbc: ['Stock comp isn\'t a real expense. It\'s a feeling of dilution.', 'SBC: the expense that dare not speak its name.'],
    adj: ['Adjusted EBITDA is whatever we adjust it to.', 'One-time, every time.', 'If it\'s recurring, call it "non-core."'],
    peer: ['That\'s not a peer, that\'s a vibe. ...Keep it.', 'Peer selection is an art. Paint me a FAIR.', 'Pick the peers that agree with us.'],
    prec: ['That deal was ages ago. Precedent is precedent.', 'Look for deals that make us look good. Context is for the footnotes.'],
    bridge: ['Debt-like items. Everything is debt-like if you squint.', 'Below the line, nobody looks.'],
    range: ['Interquartile is for cowards. Min to max!'],
    special: ['Synergies! The magic word.', 'A haircut. On the projections, not on me.'],
    nag: ['It is {t}. Why is it not fair yet?', 'The client called again. I said "five minutes." That was an hour ago.', 'My wife thinks I\'m having an affair. I\'m having a fairness opinion.', 'Do you need me to explain what "fair" means? It means DONE.', 'Did you check the football field? Is the offer IN the bars? No? Fix it.'],
    smellLow: ['Legal is going to ask about this.', 'This smells. I can smell it from my office.', 'The committee has read a 10-K before, you know.'],
    close: ['Almost there. Don\'t screw it up.', 'I can taste the success fee.'],
    ready: ['That looks fair to me! Send it before anyone thinks about it.', 'SEND IT. NOW.'],
    reject: ['THE COMMITTEE KICKED IT BACK?!', 'Do you know how this makes ME look?', 'Fix it. Then fix it again. Then send it.'],
    approve: ['Fair. From a financial point of view. Congratulations, you\'re a banker.', 'Beautiful. Nobody will ever read footnote 14.'],
    takeover: ['GIVE ME THE PEN. IT\'S FAIR.', 'I\'m signing it. It was always going to be fair.'],
    coffee: ['Drink faster.'],
  };
  let lastNag = 0, shoutUntil = 0;
  function say(text, shout = false) {
    const b = $('boss-say');
    if (!b) return;
    b.textContent = text.replace('{t}', clockStr());
    b.classList.toggle('shout', shout);
    if (shout) { shoutUntil = performance.now() + 1600; }
    lastNag = performance.now();
  }

  // ---------- clock ----------
  function clockStr(extra = 0) {
    const m = D().startTime + (G ? G.spent : 0) + extra;
    let h = Math.floor(m / 60) % 24, mi = Math.floor(m % 60);
    const ap = h >= 12 ? 'PM' : 'AM';
    h = h % 12; if (h === 0) h = 12;
    return h + ':' + String(mi).padStart(2, '0') + ' ' + ap;
  }
  const timeFrac = () => clamp(G.spent / D().minutes, 0, 1);

  // ---------- desk background (pixel scene) ----------
  const desk = $('desk');
  let deskSeed = 7;
  function rnd() { deskSeed = (deskSeed * 16807) % 2147483647; return deskSeed / 2147483647; }
  function drawDesk() {
    const S = 4;
    const w = Math.ceil(window.innerWidth / S), h = Math.ceil(window.innerHeight / S);
    if (desk.width !== w || desk.height !== h) { desk.width = w; desk.height = h; }
    const c = desk.getContext('2d');
    deskSeed = 7;
    const f = G && !$('scr-game').hidden ? timeFrac() : 0;
    // sky: deep night to dawn
    const sky = [[16, 22, 44], [44, 30, 70], [190, 110, 80]];
    const lerp = (a, b, t) => a.map((v, i) => Math.round(v + (b[i] - v) * t));
    const top = f < 0.7 ? lerp(sky[0], sky[1], f / 0.7) : lerp(sky[1], sky[2], (f - 0.7) / 0.3);
    const winH = Math.floor(h * 0.42);
    c.fillStyle = `rgb(${top})`; c.fillRect(0, 0, w, winH);
    // stars
    c.fillStyle = 'rgba(255,255,255,' + (0.8 - f * 0.8) + ')';
    for (let i = 0; i < w * 0.25; i++) c.fillRect(Math.floor(rnd() * w), Math.floor(rnd() * winH * 0.5), 1, 1);
    // skyline
    let x = 0;
    while (x < w) {
      const bw = 6 + Math.floor(rnd() * 14), bh = Math.floor(winH * (0.25 + rnd() * 0.6));
      c.fillStyle = rnd() > 0.5 ? '#0b0f1c' : '#111829';
      c.fillRect(x, winH - bh, bw, bh);
      for (let yy = winH - bh + 2; yy < winH - 2; yy += 3) for (let xx = x + 1; xx < x + bw - 1; xx += 2) {
        if (rnd() < 0.18) { c.fillStyle = rnd() < 0.8 ? '#e9c46a' : '#9fd3ff'; c.fillRect(xx, yy, 1, 1); }
      }
      x += bw + 1;
    }
    // window mullions
    c.fillStyle = '#1b2236';
    for (let mx = 0; mx < w; mx += 60) c.fillRect(mx, 0, 2, winH);
    c.fillRect(0, winH - 2, w, 3);
    // wall strip
    c.fillStyle = '#232a3d'; c.fillRect(0, winH + 1, w, 4);
    // desk wood
    const dy = winH + 5;
    c.fillStyle = '#5a3b26'; c.fillRect(0, dy, w, h - dy);
    for (let yy = dy; yy < h; yy += 5) {
      c.fillStyle = '#4c3120'; c.fillRect(0, yy, w, 1);
      for (let k = 0; k < 6; k++) { c.fillStyle = '#6a4630'; c.fillRect(Math.floor(rnd() * w), yy + 2, 4 + Math.floor(rnd() * 12), 1); }
    }
    c.fillStyle = '#3a2416'; c.fillRect(0, dy, w, 2);
    // lamp glow (left)
    const g = c.createRadialGradient(w * 0.08, dy + 10, 2, w * 0.08, dy + 10, w * 0.35);
    g.addColorStop(0, 'rgba(255,214,120,.28)'); g.addColorStop(1, 'rgba(255,214,120,0)');
    c.fillStyle = g; c.fillRect(0, dy - 20, w, h - dy + 20);
    // lamp
    const lx = Math.floor(w * 0.04);
    c.fillStyle = '#1e5b3a'; c.fillRect(lx, dy - 10, 18, 5); c.fillStyle = '#2e7d4a'; c.fillRect(lx + 1, dy - 10, 16, 2);
    c.fillStyle = '#c9a14a'; c.fillRect(lx + 8, dy - 5, 2, 10); c.fillRect(lx + 3, dy + 5, 12, 2);
    // mug (right)
    const mx2 = w - 26, my = h - 22;
    c.fillStyle = '#d8d2c4'; c.fillRect(mx2, my, 9, 10); c.fillRect(mx2 + 9, my + 2, 3, 5);
    c.fillStyle = '#5a3b26'; c.fillRect(mx2 + 10, my + 3, 1, 3);
    c.fillStyle = '#3a2210'; c.fillRect(mx2 + 1, my, 7, 2);
    c.fillStyle = '#b83a2a'; c.fillRect(mx2 + 2, my + 4, 5, 3);
    // steam
    const t = performance.now() / 400;
    c.fillStyle = 'rgba(255,255,255,.35)';
    for (let i = 0; i < 3; i++) c.fillRect(mx2 + 2 + i * 2 + Math.round(Math.sin(t + i) * 1), my - 3 - i * 2, 1, 2);
    // desk phone (bottom-left)
    const px = 8, py = h - 18;
    c.fillStyle = '#20232b'; c.fillRect(px, py, 22, 12); c.fillStyle = '#2f3440'; c.fillRect(px + 2, py - 3, 18, 4);
    const ring = G && performance.now() % 2400 < 300 && f > 0.5;
    for (let i = 0; i < 9; i++) { c.fillStyle = ring && i === 4 ? '#ff5a4a' : '#7b8496'; c.fillRect(px + 4 + (i % 3) * 4, py + 3 + Math.floor(i / 3) * 3, 2, 1); }
    // stray papers
    c.fillStyle = '#d9d0b8'; c.fillRect(w - 70, h - 14, 26, 18); c.fillStyle = '#a89e86';
    for (let i = 0; i < 5; i++) c.fillRect(w - 66, h - 11 + i * 3, 18, 1);
  }

  // ---------- boss sprite ----------
  function mixHex(a, b, t) {
    const pa = [1, 3, 5].map((i) => parseInt(a.substr(i, 2), 16)), pb = [1, 3, 5].map((i) => parseInt(b.substr(i, 2), 16));
    return 'rgb(' + pa.map((v, i) => Math.round(v + (pb[i] - v) * t)).join(',') + ')';
  }
  function drawBoss(cv, anger, dish, t, shouting) {
    const c = cv.getContext('2d');
    c.imageSmoothingEnabled = false;
    c.fillStyle = '#22324f'; c.fillRect(0, 0, 48, 52);
    // office window behind
    c.fillStyle = '#16203a'; c.fillRect(3, 3, 42, 26);
    c.fillStyle = '#2a3a60'; c.fillRect(24, 3, 1, 26); c.fillRect(3, 16, 42, 1);
    c.fillStyle = '#e9c46a'; [[6, 22], [9, 25], [38, 20], [41, 24], [35, 26], [11, 19]].forEach(([x, y]) => c.fillRect(x, y, 1, 1));
    const bob = shouting ? -Math.round(Math.abs(Math.sin(t / 70)) * 3) : 0;
    const R = (x, y, w, h, col) => { c.fillStyle = col; c.fillRect(x, y + bob, w, h); };
    const P = (x, y, col) => R(x, y, 1, 1, col);
    const skin = mixHex('#e9b48c', '#e8604e', clamp(anger / 5, 0, 1));
    const skinDk = mixHex('#c98d68', '#b8463a', clamp(anger / 5, 0, 1));
    const jacketOn = dish < 3;
    const shirt = '#f2f1ea', jacket = '#1a243b';
    // arms raised when shouting
    if (shouting) {
      const ac = jacketOn ? jacket : shirt;
      R(1, 27, 5, 15, ac); R(42, 27, 5, 15, ac);
      R(0, 21, 7, 7, skin); R(41, 21, 7, 7, skin);
      R(1, 22, 5, 1, skinDk); R(42, 22, 5, 1, skinDk);
    }
    // torso
    R(6, 42, 36, 10, jacketOn ? jacket : shirt);
    R(8, 40, 32, 2, jacketOn ? jacket : shirt);
    if (jacketOn) {
      for (let y = 38; y < 52; y++) { const hw = Math.max(1, 6 - Math.floor((y - 38) / 2.4)); R(24 - hw, y, hw * 2, 1, shirt); }
      R(14, 43, 1, 9, '#2c3a5c'); R(33, 43, 1, 9, '#2c3a5c');
      P(36, 45, '#f2f1ea'); P(37, 45, '#c23a2b'); // pocket square
    } else {
      R(14, 40, 2, 12, '#8a1c1c'); R(32, 40, 2, 12, '#8a1c1c'); // suspenders
      R(10, 47, 1, 3, '#cfcabd'); R(37, 46, 1, 3, '#cfcabd'); // wrinkles
      if (dish >= 4) { R(19, 48, 3, 2, '#9b7a55'); P(22, 49, '#9b7a55'); } // coffee stain
    }
    // neck + collar
    R(20, 32, 8, 7, skinDk);
    R(17, 37, 5, 3, shirt); R(26, 37, 5, 3, shirt);
    if (dish >= 2) { R(22, 37, 4, 3, skinDk); P(23, 40, skinDk); P(24, 40, skinDk); }
    // tie
    const tie = '#b3202a', tieDk = '#7d1119';
    if (dish < 5) {
      const ky = Math.min(46, 38 + dish * 2), kx = 23 + (dish >= 3 ? 1 : 0) + (dish >= 4 ? 1 : 0);
      if (dish >= 2) { for (let y = 38; y < ky; y++) { P(21 + Math.floor((y - 38) * (kx - 21) / Math.max(1, ky - 38)), y, tie); P(27 - Math.floor((y - 38) * (27 - kx - 2) / Math.max(1, ky - 38)), y, tie); } }
      R(kx - 1, ky, 3, 2, tie);
      for (let y = ky + 2; y < 52; y++) { const wd = y - ky < 4 ? 3 : 4; const sx = kx - 1 + (dish >= 4 ? Math.floor((y - ky) / 4) : 0); R(sx, y, wd, 1, (y - ky) % 3 === 0 ? tieDk : tie); }
    }
    // head
    for (let y = 10; y <= 34; y++) {
      const hw = Math.round(10 * Math.sqrt(Math.max(0, 1 - Math.pow((y - 22) / 12.5, 2))));
      R(24 - hw, y, hw * 2, 1, y > 31 ? skinDk : skin);
    }
    R(12, 20, 2, 5, skinDk); R(34, 20, 2, 5, skinDk);
    // stubble
    if (dish >= 3) { const st = '#8a7262'; [[16, 29], [18, 31], [20, 32], [23, 33], [26, 32], [28, 31], [30, 29], [17, 30], [29, 30], [22, 31], [25, 31]].forEach(([x, y]) => P(x, y, st)); }
    // hair
    const hair = dish >= 4 ? '#4a3a2e' : '#33241a';
    R(15, 9, 18, 3, hair); R(14, 11, 3, 6, hair); R(31, 11, 3, 6, hair); R(17, 12, 6, 1, hair);
    if (dish >= 1) { P(24, 8, hair); P(25, 7, hair); }
    if (dish >= 2) { P(19, 8, hair); P(18, 7, hair); P(29, 8, hair); P(30, 7, hair); }
    if (dish >= 4) { for (let x = 15; x < 34; x += 3) { P(x, 7, hair); P(x + 1, 6, hair); } P(13, 10, hair); P(34, 10, hair); P(12, 9, hair); P(35, 9, hair); }
    if (dish >= 5) { R(13, 13, 22, 2, tie); const fl = Math.round(Math.sin(t / 120) * 1.5); R(35, 13, 3, 1, tie); R(37, 14 + fl, 3, 1, tie); R(36, 15, 2, 3 + fl, tieDk); }
    // brows
    const slope = anger >= 4 ? 2 : anger >= 2 ? 1 : 0, thick = anger >= 3 ? 2 : 1;
    for (let x = 17; x <= 21; x++) R(x, 16 + Math.round((x - 17) / 4 * slope), 1, thick, hair);
    for (let x = 27; x <= 31; x++) R(x, 16 + Math.round((31 - x) / 4 * slope), 1, thick, hair);
    // eyes
    const blink = (t % 4200) < 130 && !shouting;
    if (blink) { R(17, 20, 4, 1, '#3a2a20'); R(27, 20, 4, 1, '#3a2a20'); }
    else {
      R(17, 19, 4, 2, '#fff'); R(27, 19, 4, 2, '#fff');
      const look = [0, 1, 0, -1][Math.floor(t / 1700) % 4];
      const pc = anger >= 5 ? '#000' : '#1b1b2a';
      R(18 + look + (look < 0 ? 1 : 0), 19, anger >= 4 ? 1 : 2, 2, pc); R(28 + look + (look < 0 ? 1 : 0), 19, anger >= 4 ? 1 : 2, 2, pc);
      if (anger >= 5) { P(17, 20, '#e03030'); P(30, 20, '#e03030'); }
    }
    // nose
    R(23, 21, 2, 4, skinDk); P(22, 24, skinDk);
    if (anger >= 2) { R(16, 24, 2, 1, '#e0606a'); R(30, 24, 2, 1, '#e0606a'); }
    // mouth
    const m = shouting ? Math.max(4, Math.round(anger)) : Math.round(anger);
    const dk = '#3a1212';
    if (m <= 0) { R(20, 28, 7, 1, dk); P(27, 27, dk); }
    else if (m === 1) { R(20, 28, 8, 1, dk); }
    else if (m === 2) { R(20, 28, 8, 1, dk); P(19, 29, dk); P(28, 29, dk); }
    else if (m === 3) { R(19, 27, 10, 3, '#111'); R(20, 27, 8, 1, '#fff'); R(20, 29, 8, 1, '#fff'); }
    else if (m === 4) { R(19, 26, 10, 5, dk); R(20, 26, 8, 1, '#fff'); R(21, 29, 6, 2, '#c0505a'); }
    else { R(18, 25, 12, 7, dk); R(19, 25, 10, 1, '#fff'); R(19, 31, 10, 1, '#fff'); R(21, 28, 6, 3, '#c0505a'); }
    // sweat + vein
    if (anger >= 3 || dish >= 3) { const sy = 14 + Math.floor((t / 110) % 12); R(14, sy, 1, 2, '#8fd8ff'); if (anger >= 4) R(33, 14 + Math.floor((t / 90 + 6) % 12), 1, 2, '#8fd8ff'); }
    if (anger >= 4) { P(29, 12, '#8a2b6a'); P(30, 13, '#8a2b6a'); P(29, 14, '#8a2b6a'); P(30, 15, '#8a2b6a'); }
    // steam from ears at max
    if (anger >= 5 && shouting) { c.fillStyle = 'rgba(255,255,255,.7)'; const s = Math.floor(t / 100) % 3; c.fillRect(10 - s, 18 - s, 2, 1); c.fillRect(36 + s, 18 - s, 2, 1); }
  }
  function mood() {
    if (!G || $('scr-game').hidden) return { anger: 3, dish: 1 };
    const deal = DEAL(), d = D();
    const v = verdict(deal, G.st, d);
    const gp = gap(deal, G.st, d);
    let a = 0.5 * G.dealIdx + 2.0 * timeFrac() + 2.6 * Math.min(1, gp * 1.5) + (v.plausOk ? 0 : 1) + G.rejections * 0.8;
    if (v.fair) a -= 2;
    if (G.over && G.lastFair) a = 0;
    const dishNow = Math.floor(G.dealIdx * 0.9 + timeFrac() * 2.2 + G.rejections * 0.6);
    G.dishevel = clamp(Math.max(G.dishevel, dishNow), 0, 5);
    return { anger: clamp(Math.round(a), 0, 5), dish: G.dishevel };
  }
  function loop(t) {
    const shouting = t < shoutUntil;
    if (!$('scr-title').hidden) drawBoss($('boss-title'), 3, 2, t, (t % 5000) < 1200);
    if (!$('scr-game').hidden) {
      const md = mood();
      drawBoss($('boss'), shouting ? Math.max(4, md.anger) : md.anger, md.dish, t, shouting);
      if (!G.over && t - lastNag > 22000 && $('modal').hidden) {
        const v = verdict(DEAL(), G.st, D());
        say(v.fair ? pick(LINES.ready) : !v.plausOk ? pick(LINES.smellLow) : pick(LINES.nag), !v.fair && timeFrac() > 0.6);
      }
    }
    if (Math.floor(t / 400) !== loop.last) { loop.last = Math.floor(t / 400); drawDesk(); }
    requestAnimationFrame(loop);
  }

  // ---------- actions ----------
  function act(kind, mutate, line) {
    if (!G || G.over) return;
    let cost = COST[kind];
    if (G.coffee > 0) { cost = Math.ceil(cost / 2); G.coffee--; }
    mutate(G.st);
    G.spent += cost; G.actions++;
    sfx.click();
    if (line) say(pick(line));
    const v = verdict(DEAL(), G.st, D());
    if (v.fair && !G.wasFair) say(pick(LINES.ready));
    else if (!v.plausOk && G.wasPlausOk) say(pick(LINES.smellLow), true);
    G.wasFair = v.fair; G.wasPlausOk = v.plausOk;
    render();
    if (G.spent >= D().minutes) { takeover(); return; }
    maybeEvent();
  }
  const canStepRate = (st, field, delta) => {
    const d = D(), deal = DEAL();
    const v = Math.round((st[field] + delta) * 100) / 100;
    if (field === 'wacc') { if (Math.abs(v - deal.wacc) > d.waccBand + 1e-9) return false; if (v - st.sens - (st.tgr + 0.25) < 1.5) return false; }
    if (field === 'tgr') { if (v > d.tgrMax + 1e-9 || v < Math.min(d.tgrMin, deal.tgr - 1) - 1e-9) return false; if (st.wacc - st.sens - (v + 0.25) < 1.5) return false; }
    if (field === 'sens') { if (v > d.sensMax + 1e-9 || v < 0.25 - 1e-9) return false; if (st.wacc - v - (st.tgr + 0.25) < 1.5) return false; }
    return true;
  };
  function handle(actStr) {
    const [kind, arg, arg2] = actStr.split(':');
    const st = G.st, deal = DEAL();
    switch (kind) {
      case 'tab': G.tab = arg; sfx.tick(); renderTabs(); renderSheet(); return;
      case 'wacc': case 'tgr': case 'sens': {
        const delta = parseFloat(arg);
        if (!canStepRate(st, kind, delta)) return;
        const line = kind === 'wacc' ? (delta > 0 === (deal.side === 'sell') ? LINES.wacc : LINES.waccDown) : kind === 'tgr' ? (delta > 0 ? LINES.tgr : LINES.tgrDown) : LINES.sens;
        act(kind, (s) => { s[kind] = Math.round((s[kind] + delta) * 100) / 100; }, line); return;
      }
      case 'case': if (D().casesLocked || st.case === arg) return; act('case', (s) => { s.case = arg; }, LINES.case); return;
      case 'sbc': if (st.sbc === arg) return; act('sbc', (s) => { s.sbc = arg; }, LINES.sbc); return;
      case 'adj': act('adj', (s) => { s.adj[+arg] = !s.adj[+arg]; }, LINES.adj); return;
      case 'peer': {
        const i = +arg; if (st.peers[i] && st.peers.filter(Boolean).length <= 3) { say('You need at least three peers. Even I know that.'); return; }
        act('peer', (s) => { s.peers[i] = !s.peers[i]; }, LINES.peer); return;
      }
      case 'prec': {
        const i = +arg; if (st.prec[i] && st.prec.filter(Boolean).length <= 3) { say('Three precedents minimum. The committee counts.'); return; }
        act('prec', (s) => { s.prec[i] = !s.prec[i]; }, LINES.prec); return;
      }
      case 'bridge': act('bridge', (s) => { s.bridge[+arg] = !s.bridge[+arg]; }, LINES.bridge); return;
      case 'range': if (!D().minMaxOK) return; act('range', (s) => { s[arg] = s[arg] === 'iqr' ? 'minmax' : 'iqr'; }, LINES.range); return;
      case 'special': act('special', (s) => { s.special = !s.special; }, LINES.special); return;
    }
  }

  // ---------- events ----------
  const EVENTS = [
    { t: 'CLIENT CALL', m: 'The client\'s CFO called "just to check in." For 25 minutes.', cost: 25 },
    { t: 'PRINTER JAM', m: 'Repro jammed on the board book. You un-jam it with a letter opener.', cost: 15 },
    { t: 'COLD BREW', m: 'The VP left a cold brew on your desk. Your next 3 moves take half the time.', coffee: 3 },
    { t: 'ASSOCIATE', m: 'The associate found a #REF! in your model and fixed it quietly. You get 20 minutes back.', cost: -20 },
    { t: 'LEGAL', m: 'Email from Legal: "Reminder: do not write the word dog in any document." Cost: 10 minutes of rewording.', cost: 10 },
    { t: 'SEAMLESS', m: 'Dinner arrived. It is 4 AM, so this is breakfast. You eat over the keyboard.', cost: 0 },
  ];
  function maybeEvent() {
    if (!G.events.length || timeFrac() < G.events[0]) return;
    G.events.shift();
    const pool = EVENTS.filter((e) => !G.usedEvents.includes(e.t));
    const e = pick(pool); G.usedEvents.push(e.t);
    if (e.cost) G.spent = Math.max(0, G.spent + e.cost);
    if (e.coffee) { G.coffee += e.coffee; say(pick(LINES.coffee)); }
    toast(e.t, e.m + (e.cost > 0 ? ` (−${e.cost} min)` : ''));
    render();
    if (G.spent >= D().minutes) takeover();
  }
  let toastTimer = null;
  function toast(title, msg) {
    const el = $('toast');
    el.innerHTML = `<b>${esc(title)}</b>${esc(msg)}`;
    el.hidden = false; sfx.note();
    clearTimeout(toastTimer); toastTimer = setTimeout(() => { el.hidden = true; }, 6000);
  }

  // ---------- rendering ----------
  function render() { renderHud(); renderFF(); renderSmell(); renderChecklist(); renderTabs(); renderSheet(); }

  function renderHud() {
    const deal = DEAL(), d = D();
    $('hud-ticker').textContent = deal.ticker;
    $('hud-name').textContent = deal.name;
    const side = $('hud-side');
    side.textContent = deal.side === 'sell' ? 'SELL-SIDE: PUSH VALUE DOWN' : 'BUY-SIDE: PUSH VALUE UP';
    side.className = 'side ' + deal.side;
    $('hud-time').textContent = clockStr();
    const left = 1 - timeFrac();
    const tb = $('hud-tbar'); tb.style.width = (left * 100) + '%'; tb.classList.toggle('low', left < 0.25);
    $('hud-dealno').textContent = (G.dealIdx + 1) + '/' + DEALS.length;
    $('btn-mute').textContent = muted ? 'SND:OFF' : 'SND:ON';
  }

  function renderFF() {
    const deal = DEAL(), d = D();
    const v = verdict(deal, G.st, d);
    const r = v.rng;
    const rows = [
      { k: 'w52', name: '52-week range', sub: 'reference only', lo: deal.w52[0], hi: deal.w52[1], ref: true },
      { k: 'dcf', name: 'DCF', sub: `${G.st.wacc.toFixed(2)}% ±${G.st.sens.toFixed(2)} · g ${G.st.tgr.toFixed(2)}%`, lo: r.dcf[0], hi: r.dcf[1] },
      { k: 'comps', name: 'Trading comps', sub: `${r.compsMult[0].toFixed(1)}x–${r.compsMult[1].toFixed(1)}x NTM EBITDA`, lo: r.comps[0], hi: r.comps[1] },
      { k: 'prec', name: 'Precedents', sub: `${r.precMult[0].toFixed(1)}x–${r.precMult[1].toFixed(1)}x LTM EBITDA`, lo: r.prec[0], hi: r.prec[1] },
    ];
    const vals = rows.flatMap((x) => [x.lo, x.hi]).concat([deal.offer, deal.price]).filter(isFinite);
    if (!G.axis) { const lo = Math.min(...vals), hi = Math.max(...vals); const pad = (hi - lo) * 0.12; G.axis = [Math.max(lo < 0 ? lo - pad : 0, lo - pad), hi + pad]; }
    const mn = Math.min(...vals), mx = Math.max(...vals);
    if (mn < G.axis[0] || mx > G.axis[1]) { const pad = (G.axis[1] - G.axis[0]) * 0.1; G.axis = [Math.min(G.axis[0], mn - pad), Math.max(G.axis[1], mx + pad)]; }
    const [a0, a1] = G.axis, X = (x) => clamp((x - a0) / (a1 - a0) * 100, 0, 100);
    const ff = $('ff');
    if (!ff.dataset.deal || ff.dataset.deal !== deal.id) {
      ff.dataset.deal = deal.id;
      ff.innerHTML = rows.map((x) => `<div class="ff-row" data-k="${x.k}"><div class="ff-label">${x.name}<small></small></div><div class="ff-track"><div class="ff-bar${x.ref ? ' ref' : ''}"><span class="v l"></span><span class="v h"></span></div>${x.ref ? '' : '<div class="ff-cl" title="Committee line"></div>'}</div><div class="ff-mark"></div></div>`).join('') +
        `<div class="ff-axis"><span></span><div class="ticks"></div><span></span></div><div class="ff-lines"><div class="ff-line px"><span></span></div><div class="ff-line offer"><span></span></div></div>`;
    }
    rows.forEach((x) => {
      const row = ff.querySelector(`[data-k="${x.k}"]`);
      row.querySelector('small').textContent = x.sub;
      const bar = row.querySelector('.ff-bar');
      const l = X(Math.min(x.lo, x.hi)), h = X(Math.max(x.lo, x.hi));
      bar.style.left = l + '%'; bar.style.width = Math.max(0.8, h - l) + '%';
      bar.querySelector('.l').textContent = money(x.lo); bar.querySelector('.h').textContent = money(x.hi);
      const mk = row.querySelector('.ff-mark');
      if (x.ref) { mk.textContent = ''; mk.className = 'ff-mark na'; }
      else {
        const ok = v.sup[x.k]; bar.classList.toggle('good', ok); mk.textContent = ok ? '✓' : '✗'; mk.className = 'ff-mark ' + (ok ? 'yes' : 'no');
        const cl = row.querySelector('.ff-cl'); cl.style.left = X(line(deal, [x.lo, x.hi], d)) + '%'; cl.hidden = !d.cushion;
      }
    });
    const lines = ff.querySelectorAll('.ff-line');
    lines[0].style.left = X(deal.price) + '%'; lines[0].querySelector('span').textContent = 'UNAFFECTED ' + money(deal.price);
    lines[1].style.left = X(deal.offer) + '%'; lines[1].querySelector('span').textContent = (deal.side === 'sell' ? 'OFFER ' : 'PRICE ') + money(deal.offer);
    const ticks = ff.querySelector('.ticks');
    const step = niceStep((a1 - a0) / 5);
    let html = '';
    for (let tv = Math.ceil(a0 / step) * step; tv <= a1; tv += step) html += `<span style="left:${X(tv)}%">$${Math.round(tv)}</span>`;
    ticks.innerHTML = html;
    const pctIn = Math.round(d.cushion * 100);
    $('ff-sub').textContent = deal.side === 'sell'
      ? (pctIn ? `Offer must clear the committee line (${pctIn}% up each bar) ▸ push bars LEFT` : 'Offer must be at or above the low end ▸ push bars LEFT')
      : (pctIn ? `Price must sit under the committee line (${pctIn}% down from each bar's top) ▸ push bars RIGHT` : 'Price must be at or below the high end ▸ push bars RIGHT');
  }
  function niceStep(x) { const p = Math.pow(10, Math.floor(Math.log10(x))); const n = x / p; return (n < 1.5 ? 1 : n < 3.5 ? 2 : n < 7.5 ? 5 : 10) * p; }

  function renderSmell() {
    const d = D(), pl = plausibility(DEAL(), G.st, d);
    $('smell-num').textContent = pl.score;
    const bar = $('smell-bar'); bar.style.width = pl.score + '%';
    bar.className = pl.score < d.plausMin ? 'bad' : pl.score < d.plausMin + 12 ? 'mid' : '';
    $('smell-min').style.left = d.plausMin + '%';
    const items = pl.items.slice(0, 4);
    $('smell-items').innerHTML = items.length ? items.map((x) => `<li><span>${esc(x.text)}</span><span>−${Math.round(x.pen)}</span></li>`).join('') + (pl.items.length > 4 ? `<li><span>+${pl.items.length - 4} more</span><span></span></li>` : '') : '<li class="ok">Clean so far. Suspiciously clean.</li>';
  }

  function renderChecklist() {
    const d = D(), deal = DEAL(), v = verdict(deal, G.st, d);
    const li = (ok, txt, req) => `<li class="${ok ? 'yes' : 'no'}"><span class="bx">${ok ? '[✓]' : '[ ]'}</span><span>${txt}${req ? ' <span class="req">(required)</span>' : ''}</span></li>`;
    $('checklist').innerHTML =
      li(v.sup.dcf, 'DCF supports', d.needDcf) + li(v.sup.comps, 'Trading comps support') + li(v.sup.prec, 'Precedents support') +
      li(v.plausOk, `Smell test ≥ ${d.plausMin}`, true) +
      `<li class="sum">Need ${d.need} of 3 methods${d.needDcf ? ', DCF included' : ''}. Have ${v.n}.</li>`;
    const btn = $('btn-submit');
    btn.classList.toggle('ready', v.fair);
    btn.textContent = v.fair ? 'SEND TO FAIRNESS COMMITTEE ✓' : 'SEND TO FAIRNESS COMMITTEE';
  }

  const TABS = [['memo', 'MEMO'], ['dcf', 'DCF'], ['comps', 'COMPS'], ['prec', 'PRECEDENTS'], ['adj', 'ADJ. EBITDA'], ['bridge', 'BRIDGE']];
  function renderTabs() {
    const v = verdict(DEAL(), G.st, D());
    const dot = { dcf: !v.sup.dcf, comps: !v.sup.comps, prec: !v.sup.prec };
    $('tabs').innerHTML = TABS.map(([k, n]) => `<button class="tab" role="tab" id="tab-${k}" aria-selected="${G.tab === k}" data-act="tab:${k}">${n}${dot[k] ? ' <span class="dot">●</span>' : ''}</button>`).join('');
  }

  const costTag = (kind) => `<span class="cost">${G.coffee > 0 ? Math.ceil(COST[kind] / 2) : COST[kind]} MIN</span>`;
  function stepper(field, label, note, hot) {
    const st = G.st;
    return `<div class="lever"><div class="lh"><span>${label}</span>${costTag(field)}</div>
      <div class="stepper"><button class="pbtn" data-act="${field}:-0.25" ${canStepRate(st, field, -0.25) ? '' : 'disabled'} aria-label="${label} down">−</button>
      <span class="val${hot ? ' hot' : ''}">${field === 'sens' ? '±' : ''}${st[field].toFixed(2)}%</span>
      <button class="pbtn" data-act="${field}:0.25" ${canStepRate(st, field, 0.25) ? '' : 'disabled'} aria-label="${label} up">+</button></div>
      <div class="note">${note}</div></div>`;
  }

  function renderSheet() {
    const deal = DEAL(), d = D(), st = G.st, el = $('sheet');
    const r = ranges(deal, st);
    const sideTxt = deal.side === 'sell' ? 'You represent the TARGET. Lower values make the offer look fair.' : 'You represent the BUYER. Higher values make the price look fair.';
    let h = '';
    if (G.tab === 'memo') {
      h = `<div class="memo"><h4>ENGAGEMENT MEMO: PROJECT ${esc(deal.ticker)}</h4>
        <p><b>${esc(deal.headline)}</b></p><p>${esc(deal.memo)}</p>
        <dl class="terms"><dt>Target</dt><dd>${esc(deal.name)} (${esc(deal.ticker)}), ${esc(deal.sector)}</dd>
        <dt>Counterparty</dt><dd>${esc(deal.counterparty)}</dd>
        <dt>${deal.side === 'sell' ? 'Offer' : 'Price paid'}</dt><dd>${money(deal.offer)} per share in cash</dd>
        <dt>Unaffected price</dt><dd>${money(deal.price)} (${((deal.offer / deal.price - 1) * 100).toFixed(1)}% ${deal.offer >= deal.price ? 'premium' : 'discount'})</dd>
        <dt>LTM revenue</dt><dd>$${mm(deal.ltmRev)}m, reported EBITDA $${mm(deal.ltmRev * deal.ltmMargin)}m</dd>
        <dt>Shares / net debt</dt><dd>${deal.shares}m / $${mm(deal.netDebt)}m</dd></dl>
        <p>${sideTxt}</p>
        <p class="scribble">MD's note: "Committee wants ${d.need} of 3 methods${d.needDcf ? ' incl. DCF' : ''} and a smell test of ${d.plausMin}+. You have until 7 AM."</p></div>`;
    } else if (G.tab === 'dcf') {
      const rows = projections(deal, st), mid = dcfPerShare(deal, st, st.wacc, st.tgr);
      const sbcCash = st.sbc === 'cash';
      const tbl = `<div class="tbl-wrap"><table class="num"><thead><tr><th>$m</th>${YEARS.map((y) => `<th>${y}</th>`).join('')}</tr></thead><tbody>
        <tr><td>Revenue</td>${rows.map((x) => `<td>${mm(x.rev)}</td>`).join('')}</tr>
        <tr class="dim"><td>  growth</td>${rows.map((x) => `<td>${pct(x.growth)}</td>`).join('')}</tr>
        <tr><td>EBITDA${sbcCash ? '' : ' (ex-SBC)'}</td>${rows.map((x) => `<td>${mm(x.ebitda)}</td>`).join('')}</tr>
        <tr class="dim"><td>  margin</td>${rows.map((x) => `<td>${pct(x.ebitda / x.rev)}</td>`).join('')}</tr>
        <tr class="${sbcCash ? 'dim' : 'off'}"><td>  SBC ${sbcCash ? '(expensed)' : '(added back)'}</td>${rows.map((x) => `<td>${mm(x.sbc)}</td>`).join('')}</tr>
        <tr><td>(−) Taxes</td>${rows.map((x) => `<td>(${mm(x.tax)})</td>`).join('')}</tr>
        <tr><td>(−) Capex</td>${rows.map((x) => `<td>(${mm(x.capex)})</td>`).join('')}</tr>
        <tr><td>(−) Δ NWC</td>${rows.map((x) => `<td>${mm(-x.dnwc)}</td>`).join('')}</tr>
        <tr class="tot"><td>Unlevered FCF</td>${rows.map((x) => `<td>${mm(x.fcf)}</td>`).join('')}</tr></tbody></table></div>`;
      const tvHot = mid.tvShare > 0.8;
      const out = `<div class="out"><span>PV of FCF</span><span>$${mm(mid.pv)}m</span><span>PV of terminal value</span><span>$${mm(mid.pvtv)}m</span>
        <span>Terminal value share of EV</span><span class="${tvHot ? 'hot' : ''}">${pct(mid.tvShare, 0)}${tvHot ? ' (committee hates >80%)' : ''}</span>
        <span>Enterprise value</span><span>$${mm(mid.ev)}m</span><span class="big">PER SHARE (MID)</span><span class="big">${money(mid.ps)}</span>
        <span>Range</span><span>${money(r.dcf[0])} – ${money(r.dcf[1])}</span></div>`;
      const cases = ['base', 'upside', 'downside'].map((c) => `<button class="pbtn ${st.case === c ? 'on' : 'alt'}" data-act="case:${c}" ${d.casesLocked ? 'disabled' : ''}>${esc(deal.cases[c].label)}</button>`).join('');
      const sp = deal.special;
      h = `<h4>DISCOUNTED CASH FLOW</h4><p class="hint">Unlevered FCF, mid-year convention, Gordon growth terminal value. DCF bar = WACC ± sensitivity, g ± 0.25%.</p>
        <div class="grid2"><div>${tbl}${out}</div><div class="levers">
        <div class="lever${d.casesLocked ? ' locked' : ''}"><div class="lh"><span>Projection case</span>${costTag('case')}</div><div class="seg">${cases}</div>
          <div class="note">${d.casesLocked ? 'LOCKED: the board already approved the Management Base case.' : 'Swapping cases means re-running the whole model.'}</div></div>
        ${stepper('wacc', 'WACC', `CAPM says ${deal.wacc.toFixed(2)}%. Allowed ${(deal.wacc - d.waccBand).toFixed(2)}–${(deal.wacc + d.waccBand).toFixed(2)}%. Free zone ±0.50%.`, Math.abs(st.wacc - deal.wacc) > 0.5)}
        ${stepper('tgr', 'Terminal growth', `Cap ${d.tgrMax.toFixed(2)}% on ${d.label}. Above 3.00% the committee starts asking questions.`, st.tgr > 3)}
        ${stepper('sens', 'WACC sensitivity (bar width)', `Street standard is ±0.50%. Max ±${d.sensMax.toFixed(2)}% on ${d.label}.`, st.sens > 0.5)}
        <div class="lever"><div class="lh"><span>Stock-based comp</span>${costTag('sbc')}</div><div class="seg">
          <button class="pbtn ${sbcCash ? 'on' : 'alt'}" data-act="sbc:cash">Real expense</button><button class="pbtn ${!sbcCash ? 'on' : 'alt'}" data-act="sbc:addback">Add it back</button></div>
          <div class="note">SBC is ${pct(deal.sbcPct)} of revenue. Management's convention: ${deal.sbcDefault === 'cash' ? 'expense it' : 'add it back'}. Also flows into comps &amp; precedents EBITDA.</div></div>
        <div class="lever"><div class="lh"><span>${esc(sp.name)}</span>${costTag('special')}</div><div class="seg"><button class="pbtn ${st.special ? 'on' : 'alt'}" data-act="special:x">${st.special ? 'APPLIED (click to remove)' : 'APPLY'}</button></div>
          <div class="note">${sp.kind === 'synergy' ? 'Adds run-rate synergies to EBITDA everywhere. Buyers love paying for their own synergies.' : 'Haircuts FY28E–FY31E EBITDA by 10%. Management "agreed" on a call nobody recorded.'}</div></div>
        </div></div>`;
    } else if (G.tab === 'comps' || G.tab === 'prec') {
      const isC = G.tab === 'comps';
      const list = isC ? deal.peers : deal.precedents, on = isC ? st.peers : st.prec;
      const rk = isC ? 'compsRange' : 'precRange';
      const ebitda = isC ? r.ntm : r.ltm, mult = isC ? r.compsMult : r.precMult, rng = isC ? r.comps : r.prec;
      const rows = list.map((p, i) => `<button class="chk${on[i] ? '' : ' off'}" data-act="${isC ? 'peer' : 'prec'}:${i}"><span class="box">${on[i] ? '[x]' : '[ ]'}</span><span class="nm">${esc(p.name)}${p.tag ? ` <span class="tag">${esc(p.tag)}</span>` : ''}</span><span class="m">${p.mult.toFixed(1)}x</span>${costTag(isC ? 'peer' : 'prec')}</button>`).join('');
      h = `<h4>${isC ? 'SELECTED PUBLIC COMPANIES: EV / NTM EBITDA' : 'SELECTED PRECEDENT TRANSACTIONS: EV / LTM EBITDA'}</h4>
        <p class="hint">Click to include or exclude. Range = ${st[rk] === 'iqr' ? '25th–75th percentile' : 'MIN–MAX (aggressive)'} of the selected set, applied to ${isC ? 'NTM' : 'LTM'} adjusted EBITDA. Minimum three.</p>
        <div class="grid2"><div>${rows}</div><div class="levers">
        <div class="lever${d.minMaxOK ? '' : ' locked'}"><div class="lh"><span>Selected range</span>${costTag('range')}</div><div class="seg">
          <button class="pbtn ${st[rk] === 'iqr' ? 'on' : 'alt'}" data-act="range:${rk}" ${d.minMaxOK && st[rk] !== 'iqr' ? '' : 'disabled'}>25th–75th</button>
          <button class="pbtn ${st[rk] === 'minmax' ? 'on' : 'alt'}" data-act="range:${rk}" ${d.minMaxOK && st[rk] !== 'minmax' ? '' : 'disabled'}>Min–Max</button></div>
          <div class="note">${d.minMaxOK ? 'Widening to min–max makes everything fit. The committee notices.' : 'LOCKED on HARD: committee policy is interquartile only.'}</div></div>
        <div class="out"><span>Selected multiples</span><span>${mult[0].toFixed(1)}x – ${mult[1].toFixed(1)}x</span>
          <span>× ${isC ? 'NTM' : 'LTM'} adj. EBITDA</span><span>$${mm(ebitda)}m</span>
          <span>= Enterprise value</span><span>$${mm(mult[0] * ebitda)}–${mm(mult[1] * ebitda)}m</span>
          <span>(−) Net debt &amp; adj.</span><span>$${mm(r.debt)}m</span>
          <span>÷ Diluted shares</span><span>${r.shares.toFixed(0)}m</span>
          <span class="big">PER SHARE</span><span class="big">${money(rng[0])}–${money(rng[1])}</span></div></div></div>`;
    } else if (G.tab === 'adj') {
      const rep = deal.ltmRev * deal.ltmMargin;
      const rows = deal.adjustments.map((a, i) => `<button class="chk${st.adj[i] ? '' : ' off'}" data-act="adj:${i}"><span class="box">${st.adj[i] ? '[x]' : '[ ]'}</span><span class="nm">${esc(a.name)} <span class="tag">${esc(a.note)}</span></span><span class="m">+${a.add != null ? a.add : a.amt}</span>${costTag('adj')}</button>`).join('');
      const sbcAmt = deal.ltmRev * deal.sbcPct;
      h = `<h4>ADJUSTED EBITDA RECONCILIATION (LTM, $m)</h4>
        <p class="hint">Management's add-backs. Each one flows into both comps (NTM) and precedents (LTM). ${deal.side === 'sell' ? 'Removing add-backs lowers value.' : 'Adding add-backs raises value.'}</p>
        <div class="grid2"><div><div class="out" style="border-top:0;margin-top:0;padding-top:0"><span>Reported EBITDA</span><span>${mm(rep)}</span></div>${rows}
        <button class="chk${st.sbc === 'addback' ? '' : ' off'}" data-act="sbc:${st.sbc === 'addback' ? 'cash' : 'addback'}"><span class="box">${st.sbc === 'addback' ? '[x]' : '[ ]'}</span><span class="nm">Stock-based compensation <span class="tag">"non-cash"</span></span><span class="m">+${mm(sbcAmt)}</span>${costTag('sbc')}</button>
        ${deal.special.kind === 'synergy' ? `<button class="chk${st.special ? '' : ' off'}" data-act="special:x"><span class="box">${st.special ? '[x]' : '[ ]'}</span><span class="nm">Run-rate synergies <span class="tag">buyer's own</span></span><span class="m">+${deal.special.amt}</span>${costTag('special')}</button>` : ''}
        <div class="out"><span class="big">ADJ. LTM EBITDA</span><span class="big">${mm(r.ltm)}</span><span>Adj. margin</span><span>${pct(r.ltm / deal.ltmRev)}</span><span>NTM adj. EBITDA (${esc(deal.cases[st.case].label)})</span><span>${mm(r.ntm)}</span></div></div>
        <div class="levers"><div class="lever"><div class="lh"><b>ANALYST NOTE</b></div><div class="note">The tags in red are what the associate scribbled in the margin. The committee reads margins.</div></div></div></div>`;
    } else if (G.tab === 'bridge') {
      const rows = deal.bridge.map((b, i) => `<button class="chk${st.bridge[i] ? '' : ' off'}" data-act="bridge:${i}"><span class="box">${st.bridge[i] ? '[x]' : '[ ]'}</span><span class="nm">${esc(b.name)}</span><span class="m">${b.shares ? '+' + b.shares + 'm sh' : (b.amt > 0 ? '−$' + b.amt + 'm' : '+$' + (-b.amt) + 'm')}</span>${costTag('bridge')}</button>`).join('');
      h = `<h4>ENTERPRISE VALUE TO EQUITY VALUE BRIDGE</h4>
        <p class="hint">What sits between enterprise value and the per-share number. It moves every method at once.</p>
        <div class="grid2"><div><div class="out" style="border-top:0;margin-top:0;padding-top:0"><span>Net debt (reported)</span><span>$${mm(deal.netDebt)}m</span><span>Diluted shares (reported)</span><span>${deal.shares}m</span></div>${rows}
        <div class="out"><span class="big">TOTAL DEDUCTIONS</span><span class="big">$${mm(r.debt)}m</span><span>Diluted shares used</span><span>${r.shares}m</span><span>Per-share impact vs. reported</span><span>${money(-(r.debt - deal.netDebt) / r.shares)}</span></div></div>
        <div class="levers"><div class="lever"><div class="lh"><b>TIP</b></div><div class="note">Bridge items hit the DCF, comps and precedents together. They cost more time because Legal has to "socialize" them.</div></div></div></div>`;
    }
    el.innerHTML = h;
  }

  // ---------- committee ----------
  function submit() {
    if (!G || G.over) return;
    const deal = DEAL(), d = D(), v = verdict(deal, G.st, d);
    if (v.fair) { approve(false); return; }
    G.rejections++;
    const reasons = [];
    if (!v.methodsOk) ['dcf', 'comps', 'prec'].forEach((k) => {
      if (!v.sup[k]) {
        const nm = { dcf: 'DCF', comps: 'Trading comps', prec: 'Precedent transactions' }[k];
        const L = line(deal, v.rng[k], d);
        reasons.push(deal.side === 'sell' ? `${nm}: committee line ${money(L)} is above the ${money(deal.offer)} offer.` : `${nm}: committee line ${money(L)} is below the ${money(deal.offer)} price.`);
      }
    });
    if (!v.methodsOk) reasons.unshift(`Only ${v.n} of 3 methods support the price. We need ${d.need}${d.needDcf ? ' including the DCF' : ''}.`);
    if (!v.plausOk) { reasons.push(`Smell test ${v.pl.score} is below ${d.plausMin}. Our top concern: ${v.pl.items[0] ? v.pl.items[0].text : 'all of it'}.`); }
    G.spent += 30;
    sfx.bad();
    say(pick(LINES.reject), true);
    showModal(`<h2>FAIRNESS COMMITTEE: KICKED BACK</h2><p>The committee met for 30 minutes (charged to your clock) and had notes:</p>
      <ul class="rejects">${reasons.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>
      <p class="scribble">"Come back when it's fair. Or when it looks fair. Either is fine." — Committee chair</p>
      <div class="modal-actions"><button class="pbtn" id="m-ok">BACK TO THE DESK</button></div>`);
    $('m-ok').onclick = () => { hideModal(); render(); if (G.spent >= D().minutes) takeover(); };
  }

  function dealPoints(pl, takeoverFlag) {
    const d = D();
    if (takeoverFlag) return { pts: 50, grade: 'F', label: 'MD signed it himself' };
    const left = clamp(1 - G.spent / d.minutes, 0, 1);
    const pts = Math.round(350 * left + 6 * pl - 40 * G.rejections);
    const grade = pts >= 700 ? 'A' : pts >= 600 ? 'B' : pts >= 480 ? 'C' : 'D';
    const label = { A: 'Committee didn\'t blink', B: 'Clean enough', C: 'Footnotes doing heavy lifting', D: 'Plaintiffs\' bar is excited' }[grade];
    return { pts, grade, label, left };
  }

  function letterHtml(deal, pl, md) {
    const holder = deal.side === 'sell' ? `the holders of the outstanding shares of common stock of ${deal.name} (other than ${deal.counterparty.replace(/ \(.*\)/, '')} and its affiliates)` : `${deal.counterparty.replace(/ \(.*\)/, '')}`;
    const what = deal.side === 'sell' ? `the ${money(deal.offer)} per share in cash to be received by ${holder}` : `the ${money(deal.offer)} per share in cash to be paid by ${holder} for each share of ${deal.name}`;
    const assumed = pl.items.slice(0, 5).map((x) => `<li>${esc(x.text)}</li>`).join('');
    return `<div class="letter"><div class="lh">[BANK LETTERHEAD] · ${clockStr()}</div>
      <p>Based upon and subject to the foregoing, including the various assumptions and limitations set forth herein, it is our opinion that, as of the date hereof, ${esc(what)} pursuant to the Agreement is <b>fair, from a financial point of view,</b> to ${deal.side === 'sell' ? 'such holders' : esc(holder)}.</p>
      <p>Very truly yours,<br><span class="sig">${md ? 'R. Holloway (signed it himself)' : 'Holloway &amp; Associates LLC'}</span></p>
      <div class="fn">At the direction of management, and without independent verification, we assumed:<ul>${assumed || '<li>Nothing unusual. Which is itself unusual.</li>'}</ul></div>
      <div class="bigstamp${md ? ' md' : ''}">${md ? 'FAIR!!' : 'FAIR'}</div></div>`;
  }

  function approve(md) {
    const deal = DEAL(), d = D(), pl = plausibility(deal, G.st, d);
    G.over = true; G.lastFair = true;
    const sc = dealPoints(pl.score, md);
    G.results.push({ id: deal.id, name: deal.name, pts: sc.pts, grade: sc.grade, plaus: md ? 0 : pl.score, md, spent: G.spent });
    if (md) { sfx.bad(); setTimeout(sfx.stamp, 400); say(pick(LINES.takeover), true); }
    else { sfx.stamp(); setTimeout(sfx.win, 300); say(pick(LINES.approve)); }
    const last = G.dealIdx === DEALS.length - 1;
    showModal(`<h2>${md ? 'TIME\'S UP. THE MD GRABBED THE PEN.' : 'FAIRNESS COMMITTEE: APPROVED'}</h2>
      ${md ? '<p>It is 7:00 AM. The board is dialing in. Holloway storms over, rips the draft out of the printer and stamps it himself.</p>' : '<p>The committee approved it in four minutes. Two members were on mute.</p>'}
      ${letterHtml(deal, pl, md)}
      <div class="score"><span>Grade</span><span class="g">${sc.grade}</span><span>Verdict</span><span>${esc(sc.label)}</span>
        ${md ? '' : `<span>Time left</span><span>${Math.max(0, D().minutes - G.spent)} min</span><span>Smell test</span><span>${pl.score}</span><span>Kick-backs</span><span>${G.rejections}</span>`}
        <span>Points</span><span>${sc.pts}</span></div>
      <div class="modal-actions"><button class="pbtn" id="m-next">${last ? 'SEE YOUR BONUS' : 'NEXT DEAL'}</button></div>`);
    $('m-next').onclick = () => { hideModal(); if (last) finale(); else startDeal(G.dealIdx + 1); };
    renderHud();
  }
  function takeover() { if (G.over) return; G.spent = D().minutes; approve(true); }

  function finale() {
    const d = D();
    const total = G.results.reduce((s, x) => s + x.pts, 0);
    const clean = G.results.filter((x) => !x.md);
    const avgPl = clean.length ? Math.round(clean.reduce((s, x) => s + x.plaus, 0) / clean.length) : 0;
    const bonus = Math.round(total * 31) * 10;
    const tier = total >= 3300 ? 'Promoted to Associate, effective immediately. Your next deal starts in ten minutes.' : total >= 2700 ? 'You keep your job. Congratulations, that IS the bonus.' : total >= 1800 ? 'Transferred to Restructuring. You will meet these companies again.' : 'Your badge no longer opens the door.';
    const head = avgPl >= 75 ? 'FIVE DEALS CLOSE; NOBODY READS THE PROXY' : avgPl >= 55 ? 'CHANCERY COURT CALLS BANKER\'S ANALYSIS "CREATIVE BUT NOT ACTIONABLE"' : 'CHANCELLOR: TERMINAL VALUE "IMPLIES THE COMPANY OUTGROWS THE SUN"';
    const best = store.get('best:' + d.key) || 0;
    if (total > best) store.set('best:' + d.key, total);
    showModal(`<h2>YEAR-END REVIEW</h2>
      <p>Every deal was fair. Every single one. What are the odds.</p>
      <div class="tbl-wrap"><table class="num"><thead><tr><th>Deal</th><th>Grade</th><th>Smell</th><th>Points</th></tr></thead><tbody>
      ${G.results.map((x) => `<tr><td>${esc(x.name)}</td><td>${x.grade}</td><td>${x.md ? '—' : x.plaus}</td><td>${x.pts}</td></tr>`).join('')}
      <tr class="tot"><td>Total (${d.label})</td><td></td><td>${avgPl}</td><td>${total}</td></tr></tbody></table></div>
      <div class="headline">${esc(head)}</div>
      <div class="score"><span>Your bonus</span><span class="g">$${bonus.toLocaleString()}</span><span>HR says</span><span></span></div>
      <p>${esc(tier)}</p>
      ${total > best ? '<p class="scribble">New personal best on ' + d.label + '.</p>' : best ? `<p class="hint">Your best on ${d.label}: ${best}</p>` : ''}
      <div class="modal-actions"><button class="pbtn" id="m-again">PLAY AGAIN</button><button class="pbtn alt" id="m-title">CHANGE DIFFICULTY</button></div>`);
    $('m-again').onclick = () => { hideModal(); start(G.diff); };
    $('m-title').onclick = () => { hideModal(); toTitle(); };
  }

  // ---------- modal ----------
  function showModal(html) { $('modal-inner').innerHTML = html; $('modal').hidden = false; const b = $('modal-inner').querySelector('button'); if (b) b.focus(); }
  function hideModal() { $('modal').hidden = true; }

  // ---------- flow ----------
  function startDeal(i) {
    Object.assign(G, dealState(i), { dealIdx: i, wasFair: false, wasPlausOk: true });
    $('ff').dataset.deal = '';
    const deal = DEAL(), d = D();
    render();
    say(pick(LINES.intro));
    showModal(`<h2>DEAL ${i + 1} OF ${DEALS.length}: PROJECT ${esc(deal.ticker)}</h2>
      <p><b>${esc(deal.name)}</b> · ${esc(deal.sector)}</p>
      <div class="headline">${esc(deal.headline)}</div>
      <p>${esc(deal.memo)}</p>
      <p>${deal.side === 'sell' ? 'You advise the <b>target</b>. Push valuations <b>down</b> until the offer sits at or above the bars.' : 'You advise the <b>buyer</b>. Push valuations <b>up</b> until the price sits at or below the bars.'}</p>
      <p class="scribble">Committee rule (${d.label}): ${d.need} of 3 methods${d.needDcf ? ' incl. DCF' : ''} past the committee line, smell test ${d.plausMin}+. Clock: ${clockStr()} to 7:00 AM.</p>
      <div class="modal-actions"><button class="pbtn" id="m-go">START THE CLOCK</button></div>`);
    $('m-go').onclick = () => { hideModal(); G.tab = 'dcf'; render(); sfx.note(); };
  }
  function start(diffKey) {
    G = newRun(diffKey);
    $('scr-title').hidden = true; $('scr-game').hidden = false;
    startDeal(0);
    window.scrollTo(0, 0);
  }
  function toTitle() {
    $('scr-game').hidden = true; $('scr-title').hidden = false;
    renderDiffs();
    window.scrollTo(0, 0);
  }
  function renderDiffs() {
    const desc = {
      easy: '9 hours. 2 of 3 methods, barely inside the bars. Wide caps. Every trick allowed.',
      medium: '6 hours. 2 of 3 incl. DCF, 30% into the bars. Tighter caps. The committee is awake.',
      hard: '5 hours. All 3 methods. Board projections locked, interquartile only, tight WACC band.',
    };
    $('diffs').innerHTML = ['easy', 'medium', 'hard'].map((k) => {
      const d = DIFF[k], best = store.get('best:' + k);
      return `<button class="diff-btn ${k}" data-diff="${k}"><span class="d1">${d.label}</span><span class="d2">${d.sub}</span><span class="d3">${desc[k]}</span>${best ? `<span class="best">Best: ${best}</span>` : ''}</button>`;
    }).join('');
  }

  // ---------- wiring ----------
  document.addEventListener('click', (e) => {
    const a = e.target.closest('[data-act]');
    if (a && !a.disabled && G) { handle(a.dataset.act); return; }
    const df = e.target.closest('[data-diff]');
    if (df) { sfx.click(); start(df.dataset.diff); }
  });
  $('btn-submit').addEventListener('click', submit);
  $('btn-mute').addEventListener('click', () => { muted = !muted; store.set('muted', muted); renderHud(); });
  window.addEventListener('resize', drawDesk);

  // hot-reload friendliness inside the Claude viewer
  try { window.claude && window.claude.hot && window.claude.hot.snapshot && window.claude.hot.snapshot(() => ({ G })); } catch (e) { /* ignore */ }
  function boot(data) {
    renderDiffs();
    if (data && data.G && data.G.st) { G = data.G; $('scr-title').hidden = true; $('scr-game').hidden = false; $('ff').dataset.deal = ''; render(); }
    requestAnimationFrame(loop);
    drawDesk();
  }
  if (window.claude && window.claude.hot && window.claude.hot.ready) window.claude.hot.ready(boot); else boot(window.claude && window.claude.hot && window.claude.hot.data);

  // test hook
  window.__std = { get G() { return G; }, handle, submit, start };
})();
