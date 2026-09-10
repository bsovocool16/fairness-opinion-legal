"""Which analyses the board book presents, by page and status: python3 classify_book.py <deal dir>
Reads inputs/book.txt and inputs/book_ocr.txt (if any); writes deck_analyses.json; prints the table and the regime the text suggests."""
import sys, re, json
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
from analyses import DECK_RX, REF, NUMERIC
from precedent_search import infer_regime
deal = Path(sys.argv[1]); inp = deal / "inputs"
def pages(text): return [p for p in text.split("-----PAGE-----") if p.strip()]
def classify(text):
    out = {}
    for i, p in enumerate(pages(text)):
        title = "\n".join(p.strip().split("\n")[:3]).lower(); body = p.lower()
        for key, rx in DECK_RX.items():
            hit_title = re.search(rx, title, re.I); hit_body = re.search(rx, body, re.I) and NUMERIC.search(p)
            if hit_title or hit_body:
                status = "reference" if REF.search(p) else "core"; rec = out.setdefault(key, {"status": status, "pages": [], "title_hit": False})
                rec["pages"].append(i + 1); rec["title_hit"] = rec["title_hit"] or bool(hit_title)
                if status == "core": rec["status"] = "core"
    return out
txt = (inp / "book.txt").read_text(errors="ignore") if (inp / "book.txt").exists() else ""
ocr = (inp / "book_ocr.txt").read_text(errors="ignore") if (inp / "book_ocr.txt").exists() else ""
if not txt and not ocr: sys.exit("no inputs/book.txt; run extract_text.py first")
c1, c2 = classify(txt), classify(ocr); merged = {}
for k in set(c1) | set(c2):
    a, b = c1.get(k), c2.get(k)
    merged[k] = {"status": "core" if (a and a["status"] == "core") or (b and b["status"] == "core") else "reference", "pages_text_layer": (a or {}).get("pages", []), "pages_ocr": (b or {}).get("pages", []), "title_hit": bool((a or {}).get("title_hit") or (b or {}).get("title_hit"))}
facts = json.load(open(deal / "facts.json")) if (deal / "facts.json").exists() else {}
hint = infer_regime(txt[:300000], facts.get("buyer_type"))
json.dump({"deck_analyses": {k: v["status"] for k, v in merged.items()}, "detail": merged, "regime_hint_from_text": hint, "note": "an analysis is listed when a page title or a page body carries it with numbers; 'reference' only when the page says so; pages are 1-based"}, open(deal / "deck_analyses.json", "w"), indent=1)
print(f"regime stated: {facts.get('regime', 'not stated')} | book text suggests: {hint}")
for k, v in sorted(merged.items(), key=lambda kv: (kv[1]["status"] != "core", kv[0])):
    pg = sorted(set(v["pages_text_layer"]) | set(v["pages_ocr"])); print(f"  {k:14s} {v['status']:9s} pages {pg[:12]}{' title' if v['title_hit'] else ''}")
