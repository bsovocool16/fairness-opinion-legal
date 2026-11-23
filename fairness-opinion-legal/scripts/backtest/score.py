"""Score a blind run against the sealed record, stage by stage. Pure functions over files already on disk; no network.

  score(spec, bt) -> scorecard dict, also written to <bt>/scorecard.json and <bt>/scorecard.md

Stages and metrics (references/backtest.md explains each and why):
  fetch        unaffected price, fiscal-year revenue / operating income / net income against the proxy's summary financials,
               LTM EBITDA against the advisor's LTM Adjusted EBITDA (definitions differ; reported, not penalized)
  projections  our derived projections against management's: absolute % error by year (revenue, EBITDA), CAGR gap
  valuation    per analysis: range overlap (IoU), midpoint error, where the offer sits (below / within / above) and whether
               that agrees; parameters (WACC, perpetuity growth, exit multiple, applied multiples) against the advisor's;
               peer-set overlap by name; analyses the advisor ran that the pipeline does not build (recall)
  deck         analyses in our book against the advisor's final book (precision, recall)
  letter       6-word phrase overlap with the filed letter, both directions, names and numbers masked; required elements
  section      if a draft exists (blind/draft/section.txt): share of the filed section's phrases the draft carries,
               analyses presented (precision, recall), length ratio
  bottom line  both say the consideration is fair (or not)
"""
import re, sys, json, statistics
from pathlib import Path
HERE = Path(__file__).resolve().parent; SCRIPTS = HERE.parent; sys.path.insert(0, str(SCRIPTS))
from selfscore import m6
from analyses import presented

def load(p):
    p = Path(p); return json.loads(p.read_text()) if p.exists() else None
def read(p):
    p = Path(p); return p.read_text(errors="ignore") if p.exists() else ""
def pct(a, b): return None if a is None or b in (None, 0) else round((a - b) / abs(b), 4)
def r4(x): return None if x is None else round(x, 4)
def cell(val, key):
    c = (val or {}).get("cells", {}).get(key); return None if c is None else c.get("value")
def flat(v):
    while isinstance(v, list) and len(v) == 1 and isinstance(v[0], list): v = v[0]
    return v

def iou(a, b):
    """Overlap of two ranges over their union; 0 when disjoint."""
    lo, hi = max(a[0], b[0]), min(a[1], b[1]); un = max(a[1], b[1]) - min(a[0], b[0])
    return round(max(0.0, hi - lo) / un, 4) if un > 0 else (1.0 if a == b else 0.0)
def side(offer, r):
    return "below" if offer < r[0] else "above" if offer > r[1] else "within"
def mid(r): return (r[0] + r[1]) / 2

LEGAL = re.compile(r"[,.]|\b(?:the|inc|corp|corporation|co|company|ltd|plc|llc|lp|holdings?|group|brands)\b", re.I)
def norm_name(n): return re.sub(r"\s+", " ", LEGAL.sub(" ", n.replace("&", " and "))).strip().lower()
def jaccard(a, b):
    A, B = {norm_name(x) for x in a}, {norm_name(x) for x in b}
    return round(len(A & B) / len(A | B), 4) if A | B else None

# which blind range answers which filed analysis
def blind_range(val, key, method=None):
    R = (val or {}).get("ranges", {})
    if key == "dcf":
        pick = "dcf_exit" if method == "exit" else "dcf_pgr"
        r = R.get(pick)
        return ((r["low"], r["high"]), pick) if r else (None, pick)
    r = R.get(key)
    return ((r["low"], r["high"]), key) if r else (None, None)

def fetch_stage(truth, co, terms, val, spec):
    out = {}
    up = spec.get("unaffected_price"); bu = (terms or {}).get("unaffected_price")
    out["unaffected_price"] = {"blind": bu, "actual": up, "error": pct(bu, up), "date_blind": (terms or {}).get("unaffected_date"), "date_actual": spec.get("unaffected_date")}
    hist = {}
    ann = {r["fy"]: r for r in ((co or {}).get("target", {}).get("annual") or [])}
    for fy, row in (truth.get("historicals") or {}).items():
        b = ann.get(int(fy), {})
        row = dict(row)
        if "net_income_parent" in row: row["net_income"] = row.pop("net_income_parent")   # NetIncomeLoss, the tag we read, is the parent's share
        hist[str(fy)] = {k: {"blind": b.get(k), "actual": v, "error": pct(b.get(k), v)} for k, v in row.items()}
    out["historicals"] = hist
    errs = [abs(m["error"]) for y in hist.values() for m in y.values() if m["error"] is not None]
    out["historicals_mape"] = r4(statistics.fmean(errs)) if errs else None
    lt = (truth.get("projections") or {}).get("ltm_adj_ebitda"); bl = cell(val, "h_ebitda_ltm")
    out["ltm_ebitda"] = {"blind": bl, "actual_adjusted": lt, "error": pct(bl, lt), "note": "advisor's figure is Adjusted EBITDA; ours is reported EBIT + D&A"}
    man = truth.get("manual") or {}
    for k, ours in (("fd_shares_mm", cell(val, "shares")), ("net_debt_mm", None if cell(val, "debt") is None else cell(val, "debt") - (cell(val, "cash") or 0))):
        if k in man: out[k] = {"blind": ours, "actual": man[k].get("value"), "error": pct(ours, man[k].get("value")), "source": man[k].get("source")}
    return out

def projections_stage(truth, val):
    pj = truth.get("projections")
    if not pj: return {"status": "no projections table found in the proxy"}
    years = [str(y) for y in (flat(cell(val, "dcf_years")) or [])]
    ours = {"revenue": flat(cell(val, "row_rev")) or [], "ebitda": flat(cell(val, "row_ebitda")) or []}
    rowkey = {"revenue": next((k for k in pj["rows"] if re.search(r"revenue|net sales|sales", k, re.I)), None),
              "ebitda": next((k for k in pj["rows"] if re.search(r"ebitda", k, re.I) and not re.search(r"margin", k, re.I)), None)}
    out = {"years_compared": [], "by_year": {}}
    for m, rk in rowkey.items():
        if not rk: continue
        for y, v in zip(pj["years"], pj["rows"][rk]):
            if y.startswith("stub") or y not in years or v is None: continue
            b = ours[m][years.index(y)] if years.index(y) < len(ours[m]) else None
            out["by_year"].setdefault(y, {})[m] = {"blind": r4(b), "actual": v, "error": pct(b, v)}
    out["years_compared"] = sorted(out["by_year"])
    for m in ("revenue", "ebitda"):
        e = [abs(d[m]["error"]) for d in out["by_year"].values() if m in d and d[m]["error"] is not None]
        out[f"{m}_mape"] = r4(statistics.fmean(e)) if e else None
        ys = [y for y in out["years_compared"] if m in out["by_year"][y]]
        if len(ys) >= 2:
            a0, a1 = out["by_year"][ys[0]][m], out["by_year"][ys[-1]][m]; n = int(ys[-1]) - int(ys[0])
            if a0["blind"] and a1["blind"] and a0["actual"] and a1["actual"]:
                out[f"{m}_cagr"] = {"blind": r4((a1["blind"] / a0["blind"]) ** (1 / n) - 1), "actual": r4((a1["actual"] / a0["actual"]) ** (1 / n) - 1)}
    return out

BUILT = {"comps", "dcf", "premiums", "trading_range", "lbo"}       # the analyses the lifecycle model builds
def valuation_stage(truth, val, offer):
    A = truth["section"]["analyses"]; out = {"analyses": {}, "params": {}}
    for key, rec in A.items():
        r = rec.get("range"); row = {"reference_only": rec.get("reference_only"), "built_by_pipeline": key in BUILT}
        if r: row["actual"] = [r["low"], r["high"]]
        b, which = blind_range(val, key, rec.get("method"))
        if b: row["blind"] = [r4(b[0]), r4(b[1])]; row["blind_from"] = which
        if r and b:
            ar = (r["low"], r["high"])
            row.update({"iou": iou(b, ar), "midpoint_error": pct(mid(b), mid(ar)), "offer_side": {"blind": side(offer, b), "actual": side(offer, ar)}})
            row["offer_side_agrees"] = row["offer_side"]["blind"] == row["offer_side"]["actual"]
        out["analyses"][key] = row
    core = [k for k, v in A.items() if v.get("range") and not v.get("reference_only")]
    scored = [out["analyses"][k] for k in core if "iou" in out["analyses"][k]]
    out["summary"] = {"advisor_core_analyses": core, "pipeline_covers": [k for k in core if k in BUILT],
                      "recall": round(len([k for k in core if k in BUILT]) / len(core), 4) if core else None,
                      "mean_iou": r4(statistics.fmean(x["iou"] for x in scored)) if scored else None,
                      "mean_abs_midpoint_error": r4(statistics.fmean(abs(x["midpoint_error"]) for x in scored)) if scored else None,
                      "offer_side_agreement": r4(statistics.fmean(1.0 if x["offer_side_agrees"] else 0.0 for x in scored)) if scored else None}
    dcf = (A.get("dcf") or {}).get("params", {})
    if dcf.get("discount_rate"):
        w = cell(val, "wacc"); a = statistics.fmean(dcf["discount_rate"])
        out["params"]["wacc"] = {"blind": r4(w), "actual": dcf["discount_rate"], "gap_bp": None if w is None else round((w - a) * 1e4)}
    if dcf.get("perpetuity_growth"):
        g = cell(val, "g_mid"); a = statistics.fmean(dcf["perpetuity_growth"])
        out["params"]["perpetuity_growth"] = {"blind": g, "actual": dcf["perpetuity_growth"], "gap_bp": None if g is None else round((g - a) * 1e4)}
    if dcf.get("exit_multiple"):
        out["params"]["exit_multiple"] = {"blind": cell(val, "exit_mid"), "actual": dcf["exit_multiple"]}
    cp = (A.get("comps") or {}).get("params", {})
    if cp.get("multiple_applied"):
        out["params"]["comps_multiple"] = {"blind": [cell(val, "comps_lo"), cell(val, "comps_hi")], "blind_basis": "EV / LTM EBITDA", "actual": cp["multiple_applied"], "actual_basis": cp.get("multiple_basis", "")[:120]}
    pp = (A.get("premiums") or {}).get("params", {})
    if pp.get("premium"): out["params"]["premium"] = {"blind": [cell(val, "prem_lo"), cell(val, "prem_hi")], "actual": pp["premium"]}
    peers_a = (A.get("comps") or {}).get("peers") or []; peers_b = [p.get("name") for p in (val or {}).get("peers") or []]
    out["peers"] = {"blind": peers_b, "actual": peers_a, "jaccard": jaccard(peers_b, peers_a),
                    "shared": sorted({norm_name(x) for x in peers_b} & {norm_name(x) for x in peers_a})}
    return out

def deck_stage(truth, deck):
    if not truth.get("book"): return {"status": "no final book in the record"}
    A = set(truth["book"]["analyses"]) - {"sensitivity"}; B = set((deck or {}).get("analyses") or []) - {"sensitivity"}
    return {"actual": sorted(A), "blind": sorted(B), "precision": round(len(A & B) / len(B), 4) if B else None, "recall": round(len(A & B) / len(A), 4) if A else None,
            "missing": sorted(A - B), "extra": sorted(B - A), "pages_blind": len((deck or {}).get("pages") or [])}

ELEMENTS = {"date": r"(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}",
            "fairness_conclusion": r"fair,? from a financial point of view", "reliance": r"(?:assumed and relied|relied upon and assumed|relied, without independent verification)",
            "no_independent_verification": r"without independent verification|not independently verif", "signature": r"very truly yours", "fee_disclosure": r"(?:will|is entitled to) receive a fee",
            "unaffiliated_holders": r"unaffiliated"}
def letter_stage(truth_letter, blind_letter, names, regime):
    if not truth_letter: return {"status": "no filed letter"}
    T, B = m6(truth_letter, names), m6(blind_letter, names)
    req = {k: bool(re.search(rx, blind_letter, re.I)) for k, rx in ELEMENTS.items() if k != "unaffiliated_holders" or regime == "13e-3"}
    filed = {k: bool(re.search(rx, truth_letter, re.I)) for k, rx in ELEMENTS.items() if k != "unaffiliated_holders" or regime == "13e-3"}
    return {"filed_phrases_carried": round(len(T & B) / len(T), 4) if T else None, "blind_phrases_in_filed": round(len(T & B) / len(B), 4) if B else None,
            "elements_blind": req, "elements_filed": filed, "elements_missing": sorted(k for k in filed if filed[k] and not req.get(k)),
            "words": {"blind": len(blind_letter.split()), "filed": len(truth_letter.split())}}

def section_stage(truth_section, draft, names, truth):
    if not draft: return {"status": "no draft yet (run section-draft on the blind deal folder, then score again)"}
    T, D = m6(truth_section, names), m6(draft, names); PA, PD = set(truth["section"]["presented"]), set(presented(draft))
    return {"filed_phrases_carried": round(len(T & D) / len(T), 4) if T else None, "draft_phrases_in_filed": round(len(T & D) / len(D), 4) if D else None,
            "analyses_presented": {"filed": sorted(PA), "draft": sorted(PD), "precision": round(len(PA & PD) / len(PD), 4) if PD else None, "recall": round(len(PA & PD) / len(PA), 4) if PA else None},
            "length_ratio": round(len(draft.split()) / max(1, len(truth_section.split())), 3)}

def score(spec, bt):
    bt = Path(bt); S, B = bt / "sealed", bt / "blind"; lc = B / "lifecycle"
    truth = load(S / "truth.json")
    if not truth: raise SystemExit(f"no {S / 'truth.json'}: run `backtest.py seal` first")
    co, terms, val, deck, letter = (load(lc / f) for f in ("company.json", "deal_terms.json", "valuation.json", "deck.json", "letter.json"))
    if not val: raise SystemExit(f"no {lc / 'valuation.json'}: run `backtest.py blind` first")
    names = [x for x in (spec.get("target_name"), spec.get("advisor"), spec.get("buyer"), (co or {}).get("target", {}).get("name")) if x]
    card = {"schema": "backtest_scorecard/1", "deal": spec["id"], "cutoff": spec["cutoff"], "offer_price": spec["offer_price"],
            "fetch": fetch_stage(truth, co, terms, val, spec), "projections": projections_stage(truth, val),
            "valuation": valuation_stage(truth, val, spec["offer_price"]), "deck": deck_stage(truth, deck),
            "letter": letter_stage(read(S / "opinion_letter.txt"), read(lc / "opinion_letter.txt"), names, spec.get("regime")),
            "section": section_stage(read(S / "section.txt"), read(B / "draft" / "section.txt"), names, truth),
            "bottom_line": {"blind_supported": (letter or {}).get("supported"), "actual_supported": spec.get("actual_fair", True)}}
    card["bottom_line"]["agrees"] = card["bottom_line"]["blind_supported"] == card["bottom_line"]["actual_supported"]
    audit = load(bt / "audit.json"); card["audit"] = {"passed": audit.get("passed"), "failures": len(audit.get("failures", [])), "warnings": len(audit.get("warnings", []))} if audit else {"passed": None, "note": "run `backtest.py audit` first"}
    (bt / "scorecard.json").write_text(json.dumps(card, indent=1)); (bt / "scorecard.md").write_text(markdown(card))
    return card

def f(x, p=False):
    if x is None: return "–"
    if isinstance(x, bool): return "yes" if x else "no"
    if isinstance(x, (list, tuple)): return " – ".join(f(v, p) for v in x)
    if p: return f"{x:+.1%}" if isinstance(x, float) else str(x)
    return f"{x:,.2f}" if isinstance(x, float) else str(x)

def markdown(c):
    L = [f"# Backtest scorecard: {c['deal']}", "", f"Data cutoff {c['cutoff']}; offer ${c['offer_price']:,.2f}. Leakage audit: " +
         ("passed" if c["audit"].get("passed") else "NOT RUN" if c["audit"].get("passed") is None else f"FAILED ({c['audit']['failures']} failures)") + ".", ""]
    fe = c["fetch"]; L += ["## Fetch", "", "| item | blind | filed | error |", "|---|---|---|---|",
                           f"| unaffected price ({fe['unaffected_price']['date_blind']} vs {fe['unaffected_price']['date_actual']}) | {f(fe['unaffected_price']['blind'])} | {f(fe['unaffected_price']['actual'])} | {f(fe['unaffected_price']['error'], True)} |"]
    for y, row in sorted(fe["historicals"].items()):
        for k, m in row.items(): L.append(f"| FY{y} {k} | {f(m['blind'])} | {f(m['actual'])} | {f(m['error'], True)} |")
    L.append(f"| LTM EBITDA (ours reported, filed adjusted) | {f(fe['ltm_ebitda']['blind'])} | {f(fe['ltm_ebitda']['actual_adjusted'])} | {f(fe['ltm_ebitda']['error'], True)} |")
    for k in ("fd_shares_mm", "net_debt_mm"):
        if k in fe: L.append(f"| {k} | {f(fe[k]['blind'])} | {f(fe[k]['actual'])} | {f(fe[k]['error'], True)} |")
    pj = c["projections"]; L += ["", "## Projections (ours derived from history; filed = management's)", ""]
    if "by_year" in pj:
        L += ["| year | revenue blind | revenue mgmt | error | EBITDA blind | EBITDA mgmt | error |", "|---|---|---|---|---|---|---|"]
        for y, d in sorted(pj["by_year"].items()):
            rv, eb = d.get("revenue", {}), d.get("ebitda", {})
            L.append(f"| {y} | {f(rv.get('blind'))} | {f(rv.get('actual'))} | {f(rv.get('error'), True)} | {f(eb.get('blind'))} | {f(eb.get('actual'))} | {f(eb.get('error'), True)} |")
        L += ["", f"Mean absolute error: revenue {f(pj.get('revenue_mape'), True)}, EBITDA {f(pj.get('ebitda_mape'), True)}."]
    else: L.append(pj.get("status", ""))
    v = c["valuation"]; s = v["summary"]
    L += ["", "## Valuation", "", "| analysis | blind $/sh | filed $/sh | IoU | midpoint error | offer vs range (blind / filed) |", "|---|---|---|---|---|---|"]
    for k, a in v["analyses"].items():
        tag = " (reference)" if a.get("reference_only") else "" if a.get("built_by_pipeline") else " (not built)"
        os_ = a.get("offer_side"); L.append(f"| {k}{tag} | {f(a.get('blind'))} | {f(a.get('actual'))} | {f(a.get('iou'))} | {f(a.get('midpoint_error'), True)} | {(os_['blind'] + ' / ' + os_['actual']) if os_ else '–'} |")
    L += ["", f"Pipeline covers {len(s['pipeline_covers'])} of the advisor's {len(s['advisor_core_analyses'])} core analyses ({f(s['recall'])}); mean IoU {f(s['mean_iou'])}; mean |midpoint error| {f(s['mean_abs_midpoint_error'], True)}; offer-side agreement {f(s['offer_side_agreement'])}.", ""]
    for k, p in v["params"].items(): L.append(f"- {k}: blind {f(p.get('blind'))}, filed {f(p.get('actual'))}" + (f" ({p['gap_bp']:+d} bp)" if p.get("gap_bp") is not None else "") + (f"; filed basis: {p['actual_basis']}" if p.get("actual_basis") else ""))
    pe = v["peers"]; L += [f"- peers: Jaccard {f(pe['jaccard'])}; shared {', '.join(pe['shared']) or 'none'}", f"  - blind: {', '.join(pe['blind'])}", f"  - filed: {', '.join(pe['actual'])}"]
    d = c["deck"]; L += ["", "## Deck", ""]
    L += [f"Analyses: precision {f(d.get('precision'))}, recall {f(d.get('recall'))}; missing {', '.join(d.get('missing', [])) or 'none'}; extra {', '.join(d.get('extra', [])) or 'none'}." if "recall" in d else d.get("status", "")]
    lt = c["letter"]; L += ["", "## Opinion letter", ""]
    L += [f"Filed letter's phrases carried {f(lt.get('filed_phrases_carried'))}; our phrases found in the filed letter {f(lt.get('blind_phrases_in_filed'))}; words {lt['words']['blind']} vs {lt['words']['filed']}; elements missing: {', '.join(lt['elements_missing']) or 'none'}." if "words" in lt else lt.get("status", "")]
    se = c["section"]; L += ["", "## Proxy section", ""]
    L += [f"Filed section's phrases carried {f(se['filed_phrases_carried'])}; analyses presented precision {f(se['analyses_presented']['precision'])}, recall {f(se['analyses_presented']['recall'])}; length ratio {se['length_ratio']}." if "length_ratio" in se else se.get("status", "")]
    b = c["bottom_line"]; L += ["", "## Bottom line", "", f"Blind letter supports fairness: {f(b['blind_supported'])}; filed: {f(b['actual_supported'])}; agree: {f(b['agrees'])}.", ""]
    return "\n".join(L)
