"""Precedent search for a deal folder: python3 search_deal.py <deal dir> [--top 8] [--years N] [--add <accession or URL>]
Reads facts.json (advisor, opinion_date, regime) and deck_analyses.json, sends the profile's SEC contact identity, writes
precedents/<accession>.txt and precedents/INDEX.json, prints the table. --add fetches one more filing into the set."""
import sys, os, re, json, argparse, datetime
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
PROFILE = Path.home() / ".claude" / "plugins" / "config" / "fairness-opinion-legal" / "CLAUDE.md"
def profile_value(label, default=None):
    if not PROFILE.exists(): return default
    for line in PROFILE.read_text().splitlines():
        if label.lower() in line.lower() and ":" in line:
            v = line.split(":", 1)[1].strip()
            if v and "[PLACEHOLDER" not in v: return re.sub(r"^\[DEFAULT:\s*|\]$", "", v).strip()
    return default
ap = argparse.ArgumentParser(); ap.add_argument("deal"); ap.add_argument("--top", type=int, default=None); ap.add_argument("--years", type=int, default=None); ap.add_argument("--add", default=None); a = ap.parse_args()
deal = Path(a.deal); facts = json.load(open(deal / "facts.json")); da = json.load(open(deal / "deck_analyses.json"))["deck_analyses"] if (deal / "deck_analyses.json").exists() else {}
if not os.environ.get("EDGAR_UA"):
    ua = profile_value("Contact for SEC requests")
    if not ua: sys.exit("no SEC contact identity: run /fairness-opinion-legal:cold-start-interview or set EDGAR_UA to 'Name email'")
    os.environ["EDGAR_UA"] = ua
import edgar_precedents as EP; EP.UA = {"User-Agent": os.environ["EDGAR_UA"]}
from precedent_search import find_precedents, best_section, regime_of
from analyses import presented
years = a.years or int(re.search(r"\d+", profile_value("Look-back window", "6") or "6").group(0)); top = a.top or int(re.search(r"\d+", profile_value("Precedents returned per deal", "8") or "8").group(0))
pdir = deal / "precedents"; pdir.mkdir(exist_ok=True); idx_p = pdir / "INDEX.json"; index = json.load(open(idx_p)) if idx_p.exists() else []
T = [k for k in da if k in ("comps", "precedents", "dcf", "lbo", "premiums", "trading_range", "targets", "future_price", "sotp")]
if a.add:
    m = re.search(r"\d{10}-\d{2}-\d{6}", a.add) or re.search(r"(\d{10})(\d{2})(\d{6})", a.add)
    acc = m.group(0) if m and "-" in m.group(0) else (f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None)
    if not acc: sys.exit("give an accession number (0001234567-25-012345) or a filing URL containing one")
    bank = facts["advisor"]; from precedent_search import phrases_for; phrases = phrases_for(bank)
    sec, doc, form, txt = best_section(acc, phrases)
    if not sec: sys.exit(f"no {bank} section found in {acc}")
    P = set(presented(sec)); rec = {"acc": acc, "name": "(added by user)", "date": "", "form": form, "regime": regime_of(form, txt), "presented": sorted(P), "coverage": round(len(set(T) & P) / len(T), 2) if T else None, "section_chars": len(sec), "section_path": str(pdir / f"{acc}.txt"), "added_by_user": True}
    (pdir / f"{acc}.txt").write_text(sec); index = [r for r in index if r["acc"] != acc] + [rec]
else:
    res = find_precedents(facts["advisor"], T, before=facts.get("opinion_date"), years=years, top=top, out_dir=str(pdir), regime=facts.get("regime"), log=lambda m: print(m, file=sys.stderr))
    index = [r for r in index if r.get("added_by_user")] + res
json.dump(index, open(idx_p, "w"), indent=1)
print(f"{'#':>2} {'filed':10} {'target (form)':44} {'regime':12} {'presents':44} cov")
for i, r in enumerate(sorted(index, key=lambda r: (r.get("regime") == facts.get("regime"), r.get("coverage") or 0, r.get("date") or ""), reverse=True), 1):
    print(f"{i:>2} {r.get('date') or '':10} {(r.get('name') or '')[:32] + ' (' + (r.get('form') or '') + ')':44} {r.get('regime') or '':12} {','.join(r.get('presented', []))[:44]:44} {r.get('coverage')}")
firm = sorted(p.name for p in pdir.glob("firm_*.txt")); print("firm shells in precedents/:", ", ".join(firm) if firm else "none")
