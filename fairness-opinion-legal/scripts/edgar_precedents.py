#!/usr/bin/env python3
"""Live EDGAR precedent search for a bank's fairness-opinion sections, measured against the offline library as truth.

  python3 edgar_precedents.py --bank centerview [--years 6] [--verify 6] [--targets]

Recipes: "sharp" = "opinion of <bank>" (the proxy's section heading); "broad" = "very truly yours" + bank name (the letter
sign-off near the bank, as a person would search). Forms DEFM14A, DEFM14C, SC 14D9. Sub-searches per analysis (bank name +
analysis phrase) give one accession set per analysis; a candidate is ranked for a target deal by the Jaccard overlap of
those memberships with the deal's analysis set, recency breaking ties. With --targets the ranking is checked on the test
deals of this bank (filings dated before the opinion date, the target's own filings excluded) against the offline
candidate bases. Writes results/edgar/<bank>.json."""
import json, time, re, csv, glob, sys, argparse, datetime, os, html
import requests
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
def norm(t): return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()
UA = {"User-Agent": os.environ.get("EDGAR_UA") or "fairness-opinion-legal (set EDGAR_UA to your name and email)"}   # the SEC requires a contact; the profile supplies it
FORMS = ["DEFM14A", "DEFM14C", "SC 14D9", "SC 13E3"]; GAP = float(os.environ.get("EDGAR_GAP", "0.5"))
BANK_PHRASES = {"centerview": ["Centerview Partners"], "goldman": ["Goldman Sachs"], "morganstanley": ["Morgan Stanley"], "jpmorgan": ["J.P. Morgan"], "evercore": ["Evercore"],
                "bofa": ["BofA Securities"], "citi": ["Citigroup Global Markets"], "kroll": ["Duff & Phelps", "Kroll, LLC"], "moelis": ["Moelis"], "williamblair": ["William Blair"],
                "lazard": ["Lazard"], "jefferies": ["Jefferies"], "houlihan": ["Houlihan Lokey"], "pjt": ["PJT Partners"], "macquarie": ["Macquarie Capital"], "rothschild": ["Rothschild"],
                "solomon": ["Solomon Partners", "PJ Solomon"], "barclays": ["Barclays"], "guggenheim": ["Guggenheim Securities"], "perella": ["Perella Weinberg"], "qatalyst": ["Qatalyst"], "piper": ["Piper Sandler"], "raymondjames": ["Raymond James"], "stifel": ["Stifel"], "wellsfargo": ["Wells Fargo Securities"], "rbc": ["RBC Capital Markets"], "ubs": ["UBS Securities"], "deutsche": ["Deutsche Bank Securities"], "truist": ["Truist Securities"]}
ANALYSIS_PHRASES = {"comps": ["selected public companies analysis", "selected publicly traded companies analysis", "comparable companies analysis", "selected companies analysis"],
                    "precedents": ["selected precedent transactions analysis", "precedent transactions analysis", "selected transactions analysis"], "dcf": ["discounted cash flow analysis"],
                    "lbo": ["leveraged buyout analysis"], "premiums": ["premiums paid analysis"], "trading_range": ["52-week trading range", "historical trading range", "52-week high"],
                    "targets": ["analyst price targets", "price targets"], "sotp": ["sum-of-the-parts analysis"], "future_price": ["illustrative future share price", "present value of future share price"]}
def fts(q, form, start, end, max_pages=10):
    hits, j = [], None
    for pg in range(1, max_pages + 1):
        j = None
        for attempt in range(4):
            try:
                r = requests.get("https://efts.sec.gov/LATEST/search-index", params={"q": q, "forms": form, "dateRange": "custom", "startdt": start, "enddt": end, "page": pg, "from": (pg - 1) * 100}, headers=UA, timeout=60)
                time.sleep(GAP)
                if r.status_code in (429, 503): time.sleep(5 * (attempt + 1)); continue
                j = r.json(); break
            except Exception: time.sleep(3 * (attempt + 1))
        if not j: break
        hs = j.get("hits", {}).get("hits", []); total = j.get("hits", {}).get("total", {}).get("value", 0)
        for h in hs:
            s = h.get("_source", {}); acc, doc = h["_id"].split(":", 1)
            hits.append({"acc": acc, "doc": doc, "form": s.get("form"), "date": s.get("file_date"), "names": s.get("display_names", []), "ciks": s.get("ciks", [])})
        if len(hs) < 100 or pg * 100 >= total: break
    return hits
def merged(hitlists):
    out = {}
    for hs in hitlists:
        for h in hs: out.setdefault(h["acc"], h)
    return out
def library(bank, start_year):
    """Accessions of the offline library's sections for this bank (filing year >= start_year). Test harness only."""
    from proxy_locate import locate_proxy
    rows = list(csv.DictReader(open(ROOT / "gpt_package_v6" / "precedents" / bank / "INDEX.csv"))) if (ROOT / "gpt_package_v6" / "precedents" / bank / "INDEX.csv").exists() else []
    lib = {}
    for r in rows:
        if not r["year"].isdigit() or int(r["year"]) < start_year: continue
        m = re.match(r"proxy_(\d{10}-\d{2}-\d{6})__", r["id"])
        if m: lib[m.group(1)] = r; continue
        m = re.match(r"13e3_(.+?)__", r["id"])
        if m:
            txt = (ROOT / "gpt_package_v6" / "precedents" / bank / (r["id"] + ".txt")).read_text(errors="ignore")
            htm, p, raw = locate_proxy(m.group(1), txt)
            if p: lib[p.parent.name] = r
    return lib
def html_to_text(h):
    """Filing HTML to text that keeps paragraphs (one per line) and table rows (| cell | cell |)."""
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h)
    h = re.sub(r"(?i)<tr[^>]*>", "\n| ", h); h = re.sub(r"(?i)</t[dh]>", " | ", h); h = re.sub(r"(?i)</tr>", "\n", h)
    h = re.sub(r"(?i)</(?:p|div|li|h\d|table|blockquote|ul|ol)>|<br\s*/?>|<hr[^>]*>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h)); t = re.sub("[\u200b\u200c\u200d\ufeff\u00ad]", "", t).replace("\xa0", " ")
    t = re.sub(r"[ \t]+", " ", t); t = re.sub(r" ?\n ?", "\n", t); t = re.sub(r"\n{2,}", "\n", t)
    t = re.sub(r"(?m)^\|\s*(?:\|\s*)*$\n?", "", t)                       # empty table rows
    return t
def fetch_doc(cik, acc, doc):
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/{doc}"
    for attempt in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=120); time.sleep(GAP)
            if r.status_code == 200: return html_to_text(r.text)
            time.sleep(3)
        except Exception: time.sleep(3)
    return ""
def filing_docs(acc):
    """All documents of a filing from the full-text index: [(cik, doc, file_type, form)], main document first, then the exhibits
    that can carry a proxy statement (EX-99.(A)... in a Schedule 13E-3), then the rest."""
    for attempt in range(3):
        try:
            r = requests.get("https://efts.sec.gov/LATEST/search-index", params={"q": f'"{acc}"'}, headers=UA, timeout=60); time.sleep(GAP)
            hs = [h for h in r.json().get("hits", {}).get("hits", []) if h["_id"].startswith(acc)]
            def rank(h):
                ft = (h["_source"].get("file_type") or "").upper(); form = (h["_source"].get("form") or "").upper(); doc = h["_id"].split(":", 1)[1]
                return (0 if ft == form else 1 if re.search(r"EX-99\.?\(?A\)?", ft) or re.search(r"ex-?99-?a|ex99a", doc, re.I) else 2 if not re.search(r"ex-?\d|ex99", doc, re.I) else 3)
            hs.sort(key=rank)
            return [((h["_source"].get("ciks") or [None])[0], h["_id"].split(":", 1)[1], h["_source"].get("file_type"), h["_source"].get("form")) for h in hs]
        except Exception: time.sleep(3)
    return []
def main_doc(acc):
    """(cik, document name, form) of a filing's main document, from the full-text index entries for the accession."""
    for attempt in range(3):
        try:
            r = requests.get("https://efts.sec.gov/LATEST/search-index", params={"q": f'"{acc}"'}, headers=UA, timeout=60); time.sleep(GAP)
            hs = [h for h in r.json().get("hits", {}).get("hits", []) if h["_id"].startswith(acc)]
            if not hs: return None, None, None
            main = next((h for h in hs if (h["_source"].get("file_type") or "").upper() == (h["_source"].get("form") or "").upper()), None) or next((h for h in hs if not re.search(r"ex-?\d|ex99", h["_id"].split(":", 1)[1], re.I)), hs[0])
            return (main["_source"].get("ciks") or [None])[0], main["_id"].split(":", 1)[1], main["_source"].get("form")
        except Exception: time.sleep(3)
    return None, None, None
def has_section(text, phrases):
    t = re.sub(r"\s+", " ", text)
    for ph in phrases:
        if re.search(r"opinion of (?:its |the )?(?:financial advisor[^.]{0,40})?" + re.escape(ph), t, re.I): return "heading"
        if re.search(re.escape(ph) + r".{0,300}(?:fairness opinion|opinion, dated|rendered (?:its |an )?(?:oral |written )?opinion|delivered (?:its |an )?(?:oral |written )?opinion)", t, re.I): return "opinion text"
    return None
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--bank", required=True); ap.add_argument("--years", type=int, default=6); ap.add_argument("--verify", type=int, default=6); ap.add_argument("--targets", action="store_true"); a = ap.parse_args()
    bank = a.bank; phrases = BANK_PHRASES[bank]; today = datetime.date.today(); start = (today - datetime.timedelta(days=365 * a.years)).isoformat(); end = today.isoformat()
    out = {"bank": bank, "phrases": phrases, "window": [start, end], "forms": FORMS, "recipes": {}}
    pools = {}
    for name, qf in (("sharp", lambda p: f'"opinion of {p}"'), ("broad", lambda p: f'"very truly yours" "{p}"')):
        pools[name] = merged([fts(qf(p), f, start, end) for p in phrases for f in FORMS]); out["recipes"][name] = {"pool": len(pools[name])}
    lib = library(bank, int(start[:4])); out["library"] = {"n": len(lib), "accessions": sorted(lib)}
    for name, pool in pools.items():
        hit = [acc for acc in lib if acc in pool]; out["recipes"][name].update({"library_hits": len(hit), "recall": round(len(hit) / len(lib), 2) if lib else None, "missed": sorted(set(lib) - set(pool))[:20]})
    union = merged([list(pools["sharp"].values()), list(pools["broad"].values())]); out["union_pool"] = len(union); out["union_recall"] = round(sum(1 for acc in lib if acc in union) / len(lib), 2) if lib else None
    # precision check on candidates outside the library (sharp recipe first, then broad-only)
    ver = []
    cands = [h for acc, h in pools["sharp"].items() if acc not in lib][: a.verify] + [h for acc, h in pools["broad"].items() if acc not in lib and acc not in pools["sharp"]][: a.verify]
    for h in cands:
        cik, doc, _ = main_doc(h["acc"])
        if not cik: continue
        txt = fetch_doc(cik, h["acc"], doc); ver.append({"acc": h["acc"], "recipe": "sharp" if h["acc"] in pools["sharp"] else "broad", "form": h["form"], "date": h["date"], "names": h["names"][:2], "section": has_section(txt, phrases) if txt else "fetch failed", "chars": len(txt)})
    out["verification"] = ver
    # analysis sub-searches (sharp recipe pool as the candidate set; broad adds candidates the sharp recipe missed)
    A = {}
    for label, aps in ANALYSIS_PHRASES.items(): A[label] = set(merged([fts(f'"{p}" "{ph}"', f, start, end) for p in phrases for ph in aps for f in FORMS]))
    out["analysis_sets"] = {k: len(v) for k, v in A.items()}
    memb = {acc: sorted(l for l, s in A.items() if acc in s) for acc in union}; out["candidates"] = [{"acc": acc, "doc": h["doc"], "date": h["date"], "form": h["form"], "names": h["names"][:1], "in_library": acc in lib, "analyses": memb[acc]} for acc, h in sorted(union.items(), key=lambda kv: kv[1]["date"] or "", reverse=True)]
    if a.targets:
        checks = []
        for fp in glob.glob(str(ROOT / "gpt_package_v6" / "test" / "*" / "facts.json")):
            facts = json.load(open(fp))
            if facts.get("bank") != bank: continue
            pid = Path(fp).parent.name; da = json.load(open(ROOT / "gpt_package_v6" / "hints" / pid / "deck_analyses.json")).get("deck_analyses", {})
            T = {k for k, s in da.items() if k in ANALYSIS_PHRASES}; cutoff = facts.get("opinion_date") or facts.get("pricing_date") or end
            tname = set(norm(facts.get("target", "")).split()) - {"inc", "corp", "corporation", "the", "company", "holdings", "group", "ltd", "plc", "llc", "co"}
            ranked = []
            for acc, h in union.items():
                if (h["date"] or "") >= cutoff: continue
                if tname and any(len(tname & set(norm(n).split())) >= max(1, len(tname) - 1) for n in h["names"]): continue
                F = set(memb[acc]); jac = len(T & F) / len(T | F) if (T | F) else 0
                ranked.append((round(jac, 3), h["date"], acc, h["names"][:1], sorted(F)))
            ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
            rat = json.load(open(ROOT / "gpt_package_v6" / "hints" / pid / "shell_rationale.json")) if (ROOT / "gpt_package_v6" / "hints" / pid / "shell_rationale.json").exists() else {}
            offline = []
            for c in (rat.get("candidates") or rat.get("bases") or []):
                cid = c.get("id") if isinstance(c, dict) else c
                m = re.match(r"proxy_(\d{10}-\d{2}-\d{6})__", cid or "")
                if m: offline.append(m.group(1))
                else:
                    m2 = re.match(r"13e3_(.+?)__", cid or "")
                    if m2:
                        rows = {r["id"]: r for r in csv.DictReader(open(ROOT / "gpt_package_v6" / "precedents" / bank / "INDEX.csv"))}
                        if cid in rows:
                            txt = (ROOT / "gpt_package_v6" / "precedents" / bank / (cid + ".txt")).read_text(errors="ignore"); htm, p, raw = locate_proxy(m2.group(1), txt)
                            if p: offline.append(p.parent.name)
            top3 = [r[2] for r in ranked[:3]]
            checks.append({"pair": pid, "target_analyses": sorted(T), "cutoff": cutoff, "candidates_before_cutoff": len(ranked), "top3": [{"acc": r[2], "jaccard": r[0], "date": r[1], "name": r[3], "analyses": r[4], "in_library": r[2] in lib} for r in ranked[:6]],
                           "offline_candidates": offline, "offline_first_in_top3": bool(offline) and offline[0] in top3, "any_offline_in_top3": any(o in top3 for o in offline), "top1_in_library": bool(top3) and top3[0] in lib})
        out["target_checks"] = checks
    od = ROOT / "gpt_package_tools" / "results" / "edgar"; od.mkdir(parents=True, exist_ok=True); json.dump(out, open(od / f"{bank}.json", "w"), indent=1)
    print(json.dumps({k: out[k] for k in ("bank", "window", "recipes", "union_pool", "union_recall")}), "| library", len(lib))
    for v in out["verification"]: print("  verify", v["recipe"], v["form"], v["date"], (v["names"] or [""])[0][:40], "->", v["section"])
    for c in out.get("target_checks", []): print("  target", c["pair"][:36], "T=", ",".join(c["target_analyses"]), "| cands", c["candidates_before_cutoff"], "| top1", c["top3"][0]["acc"] if c["top3"] else None, "jac", c["top3"][0]["jaccard"] if c["top3"] else None, "in lib", c["top1_in_library"], "| offline #1 in top3:", c["offline_first_in_top3"], "any:", c["any_offline_in_top3"])
if __name__ == "__main__": main()
