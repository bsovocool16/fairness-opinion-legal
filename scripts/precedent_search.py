#!/usr/bin/env python3
"""Find an advisor's filed fairness-opinion sections on EDGAR that best match a deal's analysis set. One callable for the
drafting skill; the search recipe inside it is the one the hit-rate test validated.

  find_precedents(bank, analyses, before=None, years=6, top=8, out_dir=None, regime=None)
      bank      bank key (centerview, goldman, ...) or the advisor's name as written
      analyses  the analyses the board book presents: any of comps, precedents, dcf, lbo, premiums, trading_range,
                targets, future_price, sotp
      before    ISO date; only filings before it (the deal's own filing must not be a precedent)
      regime    "13e-3" (going private: Schedule 13E-3 disclosure) or "conventional"; same-regime precedents rank first,
                the other regime only as fallback. infer_regime(text, buyer_type) reads it from the book or the facts.
      returns   verified sections ranked by coverage of the deal's analyses, then overlap, then recency:
                [{acc, name, date, form, url, presented, coverage, jaccard, section_chars, section_path}]

  python3 precedent_search.py --bank centerview --analyses comps,dcf,precedents,premiums --before 2025-03-01 --top 5 --out precedents_live/

Recipe: full-text search "opinion of <bank>" over DEFM14A, DEFM14C, SC 14D9 and SC 13E3 for the window (the sign-off
recipe is added only when that pool is thin); one sub-search per analysis (bank name plus the analysis phrase) gives a
preliminary ranking; the leading candidates are fetched, their section cut and its analyses read from the text, and the
ranking is redone on what the section actually presents."""
import sys, re, json, argparse, datetime, os
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import edgar_precedents as EP
from verify_candidates import section_of, presented, best_section
from bankname import bank_key
REGIME_RX = re.compile(r"rule 13e-3|schedule 13e-3|13e-3 transaction|going[- ]private transaction", re.I)
def regime_of(form, text):
    """'13e-3' for a going-private filing (Schedule 13E-3 form, or a proxy that carries the Rule 13e-3 disclosure), else 'conventional'."""
    if (form or "").upper().startswith("SC 13E3"): return "13e-3"
    return "13e-3" if len(REGIME_RX.findall(text or "")) >= 3 else "conventional"
def infer_regime(text, buyer_type=None):
    """The deal's regime from the board book or the deal facts: a buyer that is an affiliate, a controlling holder or management
    makes a Rule 13e-3 transaction; otherwise look for the going-private vocabulary in the text."""
    if buyer_type and re.search(r"controlling|insider|management|affiliate|founder|parent|majority", buyer_type, re.I): return "13e-3"
    t = text or ""
    if len(REGIME_RX.findall(t)) >= 2: return "13e-3"
    if re.search(r"special committee", t, re.I) and re.search(r"rollover|controlling (?:stock|share)holder|management buyout|affiliated (?:with|entity)|majority (?:stock|share)holder", t, re.I): return "13e-3"
    return "conventional"
def phrases_for(bank):
    key = bank if bank in EP.BANK_PHRASES else bank_key(bank)
    return EP.BANK_PHRASES.get(key, [bank])
def find_precedents(bank, analyses, before=None, years=6, top=8, out_dir=None, gap=None, log=print, regime=None):
    if gap: EP.GAP = gap
    phrases = phrases_for(bank); T = set(analyses) & set(EP.ANALYSIS_PHRASES)
    end = (before or datetime.date.today().isoformat()); start = (datetime.date.fromisoformat(end) - datetime.timedelta(days=365 * years)).isoformat()
    pool = EP.merged([EP.fts(f'"opinion of {p}"', f, start, end) for p in phrases for f in EP.FORMS])
    if len(pool) < 15: pool.update({k: v for k, v in EP.merged([EP.fts(f'"very truly yours" "{p}"', f, start, end) for p in phrases for f in EP.FORMS]).items() if k not in pool})
    pool = {acc: h for acc, h in pool.items() if (h["date"] or "") < end}
    log(f"pool: {len(pool)} filings for {phrases} in {start}..{end}")
    A = {label: set(EP.merged([EP.fts(f'"{p}" "{ph}"', f, start, end) for p in phrases for ph in EP.ANALYSIS_PHRASES[label] for f in EP.FORMS])) for label in T}
    prelim = []
    for acc, h in pool.items():
        F = {l for l, s in A.items() if acc in s}; jac = len(T & F) / len(T | F) if (T | F) else 0
        prelim.append((jac, h["date"] or "", acc))
    prelim.sort(reverse=True)
    verified = []
    for jac, date, acc in prelim[: top * 3]:
        if len(verified) >= top * 2: break
        sec, doc, form, txt = best_section(acc, phrases, hint_doc=pool[acc].get("doc"))
        if not sec or len(sec) < 6000: continue
        cik = (pool[acc]["ciks"] or [None])[0] or 0
        P = set(presented(sec)); cov = len(T & P) / len(T) if T else 0; jac2 = len(T & P) / len(T | P) if (T | P) else 0
        rec = {"acc": acc, "name": (pool[acc]["names"] or [""])[0], "date": pool[acc]["date"], "form": pool[acc]["form"], "regime": regime_of(pool[acc]["form"], txt), "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/{doc}",
               "presented": sorted(P), "coverage": round(cov, 2), "jaccard": round(jac2, 2), "section_chars": len(sec)}
        if out_dir:
            Path(out_dir).mkdir(parents=True, exist_ok=True); sp = Path(out_dir) / f"{acc}.txt"; sp.write_text(sec); rec["section_path"] = str(sp)
        verified.append(rec); log(f"  verified {acc} {rec['date']} {rec['name'][:40]} {rec['regime']} coverage {cov:.2f} presents {','.join(sorted(P))}")
    usable = [r for r in verified if r["presented"]] or verified            # a section that presents no analysis is a cover or a letter
    verified = sorted(usable, key=lambda r: (r["coverage"] + (0.15 if regime and r["regime"] == regime else 0), r["jaccard"], r["date"]), reverse=True)
    if out_dir:
        keep = {r["acc"] for r in verified[:top]}
        for r in verified[top:]:
            if r.get("section_path") and r["acc"] not in keep: Path(r["section_path"]).unlink(missing_ok=True)
    return verified[:top]
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--bank", required=True); ap.add_argument("--analyses", required=True); ap.add_argument("--before", default=None); ap.add_argument("--years", type=int, default=6); ap.add_argument("--top", type=int, default=8); ap.add_argument("--out", default=None); ap.add_argument("--regime", choices=["13e-3", "conventional"], default=None, help="the deal's regime; same-regime precedents rank first"); a = ap.parse_args()
    res = find_precedents(a.bank, a.analyses.split(","), a.before, a.years, a.top, a.out, log=lambda m: print(m, file=sys.stderr), regime=a.regime)
    if a.out: json.dump(res, open(Path(a.out) / "results.json", "w"), indent=1)
    print(json.dumps(res, indent=1))
