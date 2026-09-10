"""Shell for a deal: rank the approved precedents as bases, take the best, splice same-advisor paragraphs for analyses the
book has that the base lacks, mark what the book lacks. python3 build_shell.py <deal dir> [--base <accession or file stem>]
Writes shell/rationale.json, shell_suggested.txt, shell_composite.txt, shell_composite_eligible.txt, provenance.json."""
import sys, re, json, argparse, datetime
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
from analyses import HEAD, VALUATION, presented
BACK = re.compile(r"^(?:general|miscellaneous)\b|^the preparation of a (?:fairness|financial) opinion|complex (?:analytical )?process|^fees?\b|engagement letter|for (?:its|their) services|is entitled to", re.I)
SUMMARY = re.compile(r"summary of (?:the )?(?:material )?(?:financial )?analys|the following is a (?:brief )?summary", re.I)
def paragraphs(text): return [p for p in re.split(r"\n\s*\n|\n", text) if p.strip()]
def heading_of(p):
    s = p.strip()
    if s.endswith("?"): return None
    if len(s) <= 95:
        for label, rx in HEAD:
            if re.search(rx, s, re.I): return label
    m = re.match(r"^\s*([^.:\n—]{4,80})[.:—]", s)
    if m:
        for label, rx in HEAD:
            if re.search(rx, m.group(1), re.I) and not re.search(r"\b(?:performed|reviewed|calculated|compared|applied|analy[sz]ed|noted)\b", m.group(1), re.I): return label
    return None
def segment(text):
    """(front, [(label, text)], back)"""
    ps = paragraphs(text); n = len(ps)
    summ = next((i for i, p in enumerate(ps) if SUMMARY.search(p)), None)
    starts = [(i, l) for i, l in ((i, heading_of(p)) for i, p in enumerate(ps)) if l and (summ is None or i > summ)]
    if not starts: return text, [], ""
    first = starts[0][0]
    back_i = next((i for i in range(first + 1, n) if BACK.search(ps[i].strip()[:160]) and heading_of(ps[i]) in (None, "other") and i > starts[-1][0]), n)
    segs = []
    for k, (i, l) in enumerate(starts):
        j = starts[k + 1][0] if k + 1 < len(starts) else back_i
        if i >= back_i: break
        segs.append((l, "\n\n".join(ps[i:min(j, back_i)])))
    return "\n\n".join(ps[:first]), segs, "\n\n".join(ps[back_i:])
ap = argparse.ArgumentParser(); ap.add_argument("deal"); ap.add_argument("--base", default=None); a = ap.parse_args()
deal = Path(a.deal); facts = json.load(open(deal / "facts.json")); da = json.load(open(deal / "deck_analyses.json"))["deck_analyses"]; deck = set(da) & VALUATION
pdir = deal / "precedents"; index = {r["acc"]: r for r in json.load(open(pdir / "INDEX.json"))} if (pdir / "INDEX.json").exists() else {}
year = int((facts.get("opinion_date") or str(datetime.date.today()))[:4]); regime = facts.get("regime")
cands = []
for fp in sorted(pdir.glob("*.txt")):
    text = fp.read_text(errors="ignore"); rec = index.get(fp.stem, {}); P = set(rec.get("presented") or presented(text)) & VALUATION
    j = len(deck & P) / len(deck | P) if (deck | P) else 0
    reg = 0.15 if (regime and rec.get("regime") == regime) else 0.0
    struct = 0.15 * (("sotp" in deck) == ("sotp" in P))
    L = len(text); lfit = 0.1 if 18000 <= L <= 60000 else (0.0 if L >= 9000 else -0.2)
    rec_year = int(rec["date"][:4]) if rec.get("date") else year; rec_score = 0.05 * max(0, 1 - abs(year - rec_year) / 10)
    firm = 0.1 if fp.name.startswith("firm_") else 0.0
    cands.append({"score": round(j + reg + struct + lfit + rec_score + firm, 3), "id": fp.stem, "name": rec.get("name", fp.name), "date": rec.get("date", ""), "regime": rec.get("regime"), "analyses": sorted(P), "chars": L, "firm_shell": bool(firm)})
cands.sort(key=lambda c: c["score"], reverse=True)
if not cands: sys.exit("no precedents in precedents/; run search_deal.py or add a firm shell")
sel = next((c for c in cands if a.base and (c["id"] == a.base or a.base in c["id"])), cands[0])
sh = deal / "shell"; sh.mkdir(exist_ok=True)
json.dump({"deck_analyses": sorted(deck), "regime": regime, "candidates": cands[:3], "selected": sel["id"], "rule": "Jaccard of the book's valuation analyses with the precedent's + regime match + structure (sum of the parts) + length fit + recency (+ firm shell)"}, open(sh / "rationale.json", "w"), indent=1)
base = (pdir / f"{sel['id']}.txt").read_text(errors="ignore"); (sh / "shell_suggested.txt").write_text(base)
front, segs, back = segment(base); prov = {"base": sel["id"], "deck_analyses": sorted(deck), "segments": []}
if not segs:
    (sh / "shell_composite.txt").write_text(base); (sh / "shell_composite_eligible.txt").write_text(base); prov["note"] = "base could not be segmented; composite = base"
else:
    have = {l for l, _ in segs}; out = [front]
    for l, t in segs:
        tag = "" if (l in deck or l == "other") else "[[NOT IN THIS BOOK: delete this analysis unless the book contains it]]\n"
        out.append(tag + t); prov["segments"].append({"label": l, "source": sel["id"], "in_book": l in deck or l == "other"})
    donors = [(c["id"], (pdir / f"{c['id']}.txt").read_text(errors="ignore")) for c in cands if c["id"] != sel["id"]]
    for l in [l for l in ("comps", "precedents", "dcf", "lbo", "sotp", "nav", "premiums", "trading_range", "targets", "future_price") if l in deck and l not in have]:
        for did, dtext in donors:
            _, dsegs, _ = segment(dtext); hit = next((t for ll, t in dsegs if ll == l and 300 <= len(t) <= 8000 and re.search(r"\d", t)), None)
            if hit: out.append(f"[[BORROWED FROM {did}: {l} paragraphs; fill with this book's facts]]\n{hit}"); prov["segments"].append({"label": l, "source": did, "borrowed": True}); break
        else: prov["segments"].append({"label": l, "source": None, "borrowed": False, "note": "no precedent in the set has this analysis"})
    if "other" not in have and (deck & {"premiums", "trading_range", "targets", "future_price"}):
        for did, dtext in donors:
            _, dsegs, _ = segment(dtext); hit = next((t for ll, t in dsegs if ll == "other"), None)
            if hit: out.append(f"[[BORROWED FROM {did}: other factors paragraphs]]\n{hit}"); prov["segments"].append({"label": "other", "source": did, "borrowed": True}); break
    out.append(back)
    (sh / "shell_composite.txt").write_text("\n\n".join(x for x in out if x.strip()))
    (sh / "shell_composite_eligible.txt").write_text("\n\n".join(re.sub(r"\[\[[^\]]*\]\]\n?", "", x) for x in out if x.strip() and not x.startswith("[[NOT IN THIS BOOK")))
json.dump(prov, open(sh / "provenance.json", "w"), indent=1)
print(f"Base: {sel['name']} {sel['date']} ({sel['regime'] or 'regime unknown'}) score {sel['score']}; has {', '.join(sel['analyses'])}")
print("Alternatives: " + "; ".join(f"{c['name'][:30]} {c['date']} ({c['score']})" for c in cands[1:3]))
print("Spliced in: " + (", ".join(f"{s['label']} from {s['source']}" for s in prov["segments"] if s.get("borrowed")) or "none"))
print("Not in this book (marked): " + (", ".join(s["label"] for s in prov["segments"] if s.get("in_book") is False) or "none"))
print("Missing with no donor: " + (", ".join(s["label"] for s in prov["segments"] if s.get("borrowed") is False and s.get("source") is None) or "none"))
print(f"Shell length: {len((sh / 'shell_composite.txt').read_text()):,} characters")
