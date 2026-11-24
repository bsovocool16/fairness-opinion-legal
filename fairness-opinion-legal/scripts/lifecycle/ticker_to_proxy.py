#!/usr/bin/env python3
"""Ticker to proxy: chain the lifecycle stages and hand a finished deal folder to the proxy-section pipeline.

  python3 ticker_to_proxy.py run <TICKER> <deal dir> --advisor "<advisor legal name>" [options]
  python3 ticker_to_proxy.py stage <fetch|terms|model|check|deck|letter|handoff> <deal dir> [options]   re-run one stage
  python3 ticker_to_proxy.py stage revalue <deal dir>      after editing model.xlsx by hand: recalculate it and refresh valuation.json
  python3 ticker_to_proxy.py status <deal dir>

Options: --buyer NAME  --buyer-type strategic|sponsor|controlling holder|management  --premium 0.30 | --offer-price 51.00
         --regime conventional|13e-3  --addressee "the Board of Directors"  --opinion-date YYYY-MM-DD  --codename "Project X"
         --peers A,B,C  --max-peers 6  --fixture <company.json> (offline: skip fetch and use this file)  --force (letter)

Stages and their files (all under <deal dir>/lifecycle/ unless noted; each reads only the files named before it):
  fetch    company.json                         SEC XBRL, prices, betas, peers (fetch_company.py)
  terms    deal_terms.json                      the hypothetical deal: unaffected price and date, offer price, parties, regime
  model    model.xlsx, model_values.xlsx, valuation.json     the Excel model and the values read back from it (build_model.py)
  check    model_check.json                     drafting-convention audit of the model (check_model.py); a failure stops the chain
  deck     board_book.pptx, board_book.pdf, deck.json        the board book (build_deck.py)
  letter   opinion_letter.txt/.docx, letter.json            the opinion letter (build_letter.py)
  handoff  <deal dir>/facts.json, inputs/book.pdf, inputs/book.txt, inputs/opinion_letter.txt, deal.md, history.md,
           deck_analyses.json                   the intake the proxy pipeline expects; then precedent-search, shell, draft, redline
manifest.json records each stage's status, time and outputs."""
import sys, json, argparse, datetime, shutil, subprocess, hashlib, traceback
from pathlib import Path
HERE = Path(__file__).resolve().parent; SCRIPTS = HERE.parent; sys.path.insert(0, str(HERE))
from common import load, save, SCHEMAS
STAGES = ["fetch", "terms", "model", "check", "deck", "letter", "handoff"]
EXTRA = ["revalue"]   # not part of run: recalculates a hand-edited model.xlsx
CODENAMES = ["Atlas", "Beacon", "Cobalt", "Delta", "Ember", "Falcon", "Granite", "Harbor", "Iris", "Juniper", "Keystone", "Lantern", "Meridian", "Northstar", "Orchid", "Pinnacle", "Quartz", "Redwood", "Summit", "Tidewater"]

def paths(deal):
    lc = Path(deal) / "lifecycle"
    return {"lc": lc, "company": lc / "company.json", "terms": lc / "deal_terms.json", "valuation": lc / "valuation.json", "model": lc / "model.xlsx",
            "values": lc / "model_values.xlsx", "check": lc / "model_check.json", "deck": lc / "deck.json", "letter": lc / "letter.json", "manifest": lc / "manifest.json"}

def manifest(deal, stage, status, detail=None):
    P = paths(deal); m = load(P["manifest"]) if P["manifest"].exists() else {"stages": {}}
    m["stages"][stage] = {"status": status, "at": datetime.datetime.now().isoformat(timespec="seconds"), **({"detail": detail} if detail else {})}
    save(m, P["manifest"])

def stage_fetch(deal, a):
    P = paths(deal)
    if a.fixture:
        shutil.copy(a.fixture, P["company"]); print(f"fixture: copied {a.fixture}"); return
    import fetch_company
    fetch_company.run(a.ticker, P["lc"], a.peers.split(",") if a.peers else None, a.max_peers, a.as_of)

def stage_terms(deal, a):
    P = paths(deal); co = load(P["company"]); t = co["target"]; hist = t["price"]["history_1y"]
    od = a.opinion_date or co["as_of"]
    before = [h for h in hist if h[0] < od] or hist
    ud, up = before[-1]
    if a.offer_price: offer = float(a.offer_price)
    else: offer = round(round(up * (1 + a.premium) * 4) / 4, 2)          # to the nearest $0.25, as offers are announced
    if not a.advisor: raise SystemExit("--advisor is required: the advisor's legal name as it signs (its filed sections on EDGAR are the precedents)")
    code = a.codename or f"Project {CODENAMES[int(hashlib.md5(t['ticker'].encode()).hexdigest(), 16) % len(CODENAMES)]}"
    regime = a.regime or ("13e-3" if a.buyer_type in ("controlling holder", "management") else "conventional")
    addressee = a.addressee or ("the Special Committee of the Board of Directors" if regime == "13e-3" else "the Board of Directors")
    terms = {"schema": SCHEMAS["deal_terms"], "hypothetical": True, "ticker": t["ticker"], "target": t["name"], "advisor": a.advisor,
             "advisor_role": f"financial advisor to {addressee}", "addressee": addressee, "buyer": a.buyer, "buyer_type": a.buyer_type, "consideration": "cash",
             "unaffected_price": up, "unaffected_date": ud, "offer_price": offer, "premium": round(offer / up - 1, 4), "opinion_date": od, "regime": regime, "codename": code}
    save(terms, P["terms"]); print(f"terms: {t['ticker']} unaffected ${up:,.2f} on {ud}; offer ${offer:,.2f} ({offer / up - 1:.1%} premium) from {a.buyer} ({a.buyer_type}); {regime}; advisor {a.advisor}")

def stage_model(deal, a):
    import build_model; P = paths(deal); d = build_model.run(P["company"], P["terms"], P["lc"])
    if d["errors"]: raise SystemExit(f"model has {len(d['errors'])} formula errors: {d['errors'][:5]}")

def stage_revalue(deal, a):
    import build_model; P = paths(deal); d = build_model.revalue(P["company"], P["valuation"])
    if d["errors"]: raise SystemExit(f"model has {len(d['errors'])} formula errors: {d['errors'][:5]}")

def stage_check(deal, a):
    import check_model; P = paths(deal); F = check_model.check(P["model"], P["values"])
    save([{"rule": r, "cell": c, "detail": d} for r, c, d in F], P["check"])
    if F:
        for r, c, d in F[:20]: print(f"  {r} {c} {d}")
        raise SystemExit(f"model fails {len(F)} drafting-convention check(s); see {P['check']}")
    print("check: C1-C6 pass (colors, no hardcodes in formulas, input placement, units, no errors, no orphan inputs)")

def stage_deck(deal, a):
    import build_deck; P = paths(deal)
    if getattr(a, "advisor", None):                                     # a new advisor on a re-run: record it, so the deck, letter and handoff agree
        terms = load(P["terms"])
        if terms["advisor"] != a.advisor: terms["advisor"] = a.advisor; save(terms, P["terms"]); print(f"deal_terms.json: advisor set to {a.advisor}; re-run letter and handoff")
    build_deck.run(P["company"], P["terms"], P["valuation"], P["lc"], house_style=getattr(a, "house_style", "auto"))

def stage_letter(deal, a):
    import build_letter; P = paths(deal); build_letter.run(P["company"], P["terms"], P["valuation"], P["deck"], P["lc"], force=a.force)

def stage_handoff(deal, a):
    """Write the deal folder the proxy pipeline expects (deal-intake's outputs), then run the book classifier."""
    P = paths(deal); deal = Path(deal); terms = load(P["terms"]); co = load(P["company"]); deck = load(P["deck"]); letter = load(P["letter"])
    inp = deal / "inputs"; inp.mkdir(parents=True, exist_ok=True)
    src = deck.get("pdf") or deck["pptx"]; book = inp / ("book" + Path(src).suffix); shutil.copy(src, book)
    shutil.copy(letter["txt"], inp / "opinion_letter.txt")
    r = subprocess.run([sys.executable, str(SCRIPTS / "extract_text.py"), str(book), str(inp / "book.txt")], capture_output=True, text=True); print(r.stdout.strip() or r.stderr.strip())
    role = "Special Committee financial advisor" if "committee" in terms["addressee"].lower() else "financial advisor to the Board of Directors"
    facts = {"advisor": terms["advisor"], "role": role, "addressee": terms["addressee"], "opinion_date": terms["opinion_date"], "pricing_date": terms["unaffected_date"],
             "target": terms["target"], "ticker": terms["ticker"], "buyer": terms["buyer"], "buyer_type": terms["buyer_type"], "consideration": terms["consideration"],
             "offer_price": terms["offer_price"], "regime": terms["regime"], "hypothetical": True,
             "deck_source": {"generated_by": "ticker-to-proxy", "file": str(book), "pages": len(deck["pages"]), "ocr": False},
             "lifecycle": {"model": str(P["model"]), "valuation": str(P["valuation"]), "deck": str(P["deck"]), "letter": str(P["letter"]), "synthetic_data": bool(co.get("synthetic"))}}
    save(facts, deal / "facts.json")
    md = [f"# {deal.name}", "", f"- Target: {terms['target']} ({terms['ticker']})", f"- Buyer: {terms['buyer']} ({terms['buyer_type']}) — HYPOTHETICAL", f"- Advisor: {terms['advisor']}, {terms['advisor_role']} — illustrative; materials not prepared by the advisor",
          f"- Regime: {'Rule 13e-3 going-private' if terms['regime'] == '13e-3' else 'conventional'}", f"- Consideration: ${terms['offer_price']:,.2f} in cash per share ({terms['premium']:.1%} premium to ${terms['unaffected_price']:,.2f} on {terms['unaffected_date']}); opinion dated {terms['opinion_date']}",
          f"- Source: generated by ticker-to-proxy from public data{' (SYNTHETIC FIXTURE)' if co.get('synthetic') else ''}; model, book and letter under lifecycle/", "- Confidentiality: none; public data and hypothetical terms"]
    (deal / "deal.md").write_text("\n".join(md) + "\n")
    with open(deal / "history.md", "a") as h: h.write(f"- {datetime.date.today()} ticker-to-proxy: model, board book ({len(deck['pages'])} pp.) and opinion letter generated; intake written\n")
    r = subprocess.run([sys.executable, str(SCRIPTS / "classify_book.py"), str(deal)], capture_output=True, text=True); print(r.stdout.strip() or r.stderr.strip())
    da = load(deal / "deck_analyses.json")["deck_analyses"]; want = set(deck["analyses"]) - {"sensitivity"}
    missing = want - set(da)
    if missing: raise SystemExit(f"the classifier did not find {sorted(missing)} in the book; slide titles and scripts/analyses.py DECK_RX have drifted apart")
    print(f"handoff: {deal} ready for precedent-search (regime {terms['regime']}, analyses {', '.join(sorted(da))})")

FN = {s: globals()[f"stage_{s}"] for s in STAGES + EXTRA}

def go(deal, stages, a):
    paths(deal)["lc"].mkdir(parents=True, exist_ok=True)
    for s in stages:
        print(f"== {s}"); t0 = datetime.datetime.now()
        try: FN[s](deal, a)
        except SystemExit as e:
            manifest(deal, s, "stopped", str(e)); print(f"STOPPED at {s}: {e}"); return 2
        except Exception as e:
            manifest(deal, s, "failed", f"{type(e).__name__}: {e}"); traceback.print_exc(); return 1
        manifest(deal, s, "ok", f"{(datetime.datetime.now() - t0).total_seconds():.1f}s")
    return 0

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    def common(p):
        p.add_argument("--advisor"); p.add_argument("--buyer", default="Hypothetical Parent, LLC"); p.add_argument("--buyer-type", default="sponsor", choices=["strategic", "sponsor", "controlling holder", "management"])
        g = p.add_mutually_exclusive_group(); g.add_argument("--premium", type=float, default=0.30); g.add_argument("--offer-price", type=float)
        p.add_argument("--regime", choices=["conventional", "13e-3"]); p.add_argument("--addressee"); p.add_argument("--opinion-date"); p.add_argument("--as-of"); p.add_argument("--codename")
        p.add_argument("--peers"); p.add_argument("--max-peers", type=int, default=6); p.add_argument("--fixture"); p.add_argument("--force", action="store_true")
        p.add_argument("--house-style", default="auto", help="board-book look: auto (match the advisor), default, goldman, perella, jpm, jefferies, citi, evercore")
    r = sub.add_parser("run"); r.add_argument("ticker"); r.add_argument("deal"); common(r)
    s = sub.add_parser("stage"); s.add_argument("stage", choices=STAGES + EXTRA); s.add_argument("deal"); s.add_argument("--ticker"); common(s)
    st = sub.add_parser("status"); st.add_argument("deal")
    a = ap.parse_args()
    if a.cmd == "status":
        m = paths(a.deal)["manifest"]; print(json.dumps(load(m), indent=1) if m.exists() else "no lifecycle manifest"); sys.exit(0)
    if a.cmd == "run": sys.exit(go(a.deal, STAGES, a))
    if a.stage == "fetch" and not (a.ticker or a.fixture): sys.exit("--ticker is needed for the fetch stage")
    sys.exit(go(a.deal, [a.stage], a))
