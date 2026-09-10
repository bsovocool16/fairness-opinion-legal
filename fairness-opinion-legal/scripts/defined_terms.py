"""Defined-terms glossary from a draft proxy statement or merger agreement: python3 defined_terms.py <file> <deal dir>
Every (the "Term") definition with the sentence that defines it. Writes defined_terms.json and defined_terms.md in the deal folder."""
import re, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
from extract_text import extract
PAREN = re.compile(r"\(([^()]{1,220})\)"); QUOTED = re.compile(r"[“\"]\s*([A-Z][^”\"]{1,90}?)\s*[”\"]")
def clean(raw):
    raw = raw.replace("\x93", "“").replace("\x94", "”").replace("\x91", "‘").replace("\x92", "’").replace("\x96", "–").replace("\x97", "—")
    raw = re.sub(r"“\s+", "“", raw); raw = re.sub(r"\s+”", "”", raw); return re.sub(r"[ \t]*\n[ \t]*", "\n", raw)
def glossary(raw):
    terms, order = {}, []
    for m in PAREN.finditer(raw):
        inner = m.group(1)
        if not QUOTED.search(inner) or not re.match(r"\s*(?:the|an?|each|collectively|together|such|referred|hereinafter|as|which|and|or|[“\"])", inner, re.I): continue
        for q in QUOTED.finditer(inner):
            term = " ".join(q.group(1).split()).strip(" ,;:."); term = re.sub(r"^(?:The|the|An?|an?)\s+", "", term)
            if not term or term[:1].islower() or term in terms or len(term) > 70: continue
            a = max(0, m.start() - 600); before = raw[a:m.start()]
            cuts = [(before.rfind(". "), 2), (before.rfind("\n"), 1), (before.rfind("; "), 2)]; cut, skip = max(cuts); start = a + (cut + skip if cut >= 0 else 0)
            after = raw[m.end():m.end() + 400]; cut2 = min([x for x in (after.find(". "), after.find("\n")) if x >= 0] or [len(after)])
            terms[term] = {"term": term, "definition": " ".join(raw[start:m.end() + cut2 + 1].split())[:450]}; order.append(term)
    return [terms[t] for t in order]
src, deal = Path(sys.argv[1]), Path(sys.argv[2]); g = glossary(clean(extract(src)))
json.dump({"source": src.name, "terms": g}, open(deal / "defined_terms.json", "w"), indent=1)
(deal / "defined_terms.md").write_text(f"# Defined terms from {src.name}\n\n" + "\n".join(f"- **{t['term']}**: {t['definition']}" for t in g) + "\n")
print(f"{len(g)} defined terms from {src.name}; first: " + ", ".join(t["term"] for t in g[:15]))
