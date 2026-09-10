#!/usr/bin/env python3
"""Score a draft against everything in the deal folder except a filed section (there is none yet):
  python3 selfscore.py <deal dir> <draft.txt>
Advisor-language share (the draft's 6-word phrases, numbers and names masked, found in the precedents, the shell or the letter),
letter carry-over, shell retention, the book's analyses presented with a result, defined-term consistency, selected-company
name form, numbers not in the inputs, tables, commentary or markers, length against the base; coverage counts the analyses this
advisor's precedents present, and flags analyses outside them, reference items carried as tables, and sensitivity grids. Writes draft/selfscore.json."""
import sys, re, json, glob
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
from analyses import ANALYSES, NUMERIC, presented
SUFFIX = r"(?:inc\.?|corp\.?|corporation|co\.?|company|ltd\.?|limited|plc|llc|l\.l\.c\.|lp|l\.p\.|holdings?|group|partners|securities|capital|markets|s\.a\.|ag|n\.v\.)"
LEGAL = re.compile(r"(?:,\s*|\s+)(?:inc\.?|corp\.?|corporation|co\.?|company|ltd\.?|limited|plc|llc|l\.l\.c\.|lp|l\.p\.|s\.a\.|n\.v\.|ag|se|holdings?|group|trust|partners|bancorp|incorporated)\.?\s*$", re.I)
META = re.compile(r"drafting basis|this (benchmark )?draft|drafting assumption|not (been )?invented|\[insert|placeholder|the supplied (facts|presentation|deck|book|text|inputs)|benchmark draft|source (conflict|issue)|unrecoverable|not available in the (book|deck|inputs)|\bTODO\b|\[\[", re.I)
MARK = re.compile(r"\[\[(?:BORROWED|NOT IN THIS BOOK)[^\]]*\]\]"); REVIEWER = re.compile(r"\[REVIEWER:[^\]]*\]")
def mask(text, names):
    t = text or ""
    for n in sorted(set(names), key=len, reverse=True):
        t = re.sub(re.escape(n), " NAME ", t, flags=re.I); short = re.sub(r"[,.]", "", n).split()
        if short and len(short[0]) > 3 and short[0].lower() not in ("the", "company", "parent"): t = re.sub(r"\b" + re.escape(short[0]) + r"\b", " NAME ", t)
    t = re.sub(r"\b(?:[A-Z][\w&'’.-]*\s+){0,3}[A-Z][\w&'’.-]*,?\s+" + SUFFIX + r"\b", " NAME ", t); return re.sub(r"\d[\d,\.]*", "#", t)
def sh(text, n): toks = re.findall(r"[a-z#']+|NAME", text); return set(" ".join(toks[i:i + n]) for i in range(len(toks) - n + 1))
def m6(text, names): return sh(re.sub(r"[A-Z]", lambda c: c.group(0).lower(), mask(text, names)).replace("name", "NAME"), 6)
def cov(a, b): return round(len(a & b) / len(a), 3) if a else None
def read(p): return Path(p).read_text(errors="ignore") if Path(p).exists() else ""
def tables(text):
    tabs, cur = [], []
    for l in text.split("\n"):
        if l.strip().startswith("|"):
            if re.match(r"^\|(\s*:?-+:?\s*\|)+\s*$", l.strip()): continue
            cur.append([c.strip() for c in l.strip().strip("|").split("|")])
        elif cur: tabs.append(cur); cur = []
    if cur: tabs.append(cur)
    return tabs
def main():
    deal, draft_p = Path(sys.argv[1]), Path(sys.argv[2]); draft = read(draft_p)
    if not draft.strip(): sys.exit("empty draft")
    facts = json.load(open(deal / "facts.json")) if (deal / "facts.json").exists() else {}; names = [facts.get(k) for k in ("advisor", "target", "buyer") if facts.get(k)]
    letter, deck, ocr = read(deal / "inputs" / "opinion_letter.txt"), read(deal / "inputs" / "book.txt"), read(deal / "inputs" / "book_ocr.txt")
    comp = MARK.sub("", read(deal / "shell" / "shell_composite.txt")); elig = read(deal / "shell" / "shell_composite_eligible.txt")
    lib = set()
    for fp in glob.glob(str(deal / "precedents" / "*.txt")): lib |= m6(read(fp), [])
    D6, C6, L6, E6 = m6(draft, names), m6(comp, []) if comp else set(), m6(letter, names) if letter else set(), m6(elig, []) if elig else set()
    out = {"draft_words": len(draft.split()), "advisor_language_share": cov(D6, lib | C6 | L6) if (lib or C6 or L6) else None, "letter_carry_over": cov(L6, D6) if L6 else None, "composite_retention": cov(C6, D6) if C6 else None, "eligible_retention": cov(E6, D6) if E6 else None}
    da = json.load(open(deal / "deck_analyses.json")).get("deck_analyses", {}) if (deal / "deck_analyses.json").exists() else {}
    pres = {k: any(NUMERIC.search(draft[m.end():m.end() + 900]) for m in re.finditer(rx, draft, re.I)) for k, rx in ANALYSES.items()}
    book = [k for k in da if k in ANALYSES and da[k] in ("core", "reference")]; core = [k for k in book if da[k] == "core"]
    idx = json.load(open(deal / "precedents" / "INDEX.json")) if (deal / "precedents" / "INDEX.json").exists() else []; prec = set()
    for e in idx: prec |= set(e.get("presented") or [])
    if not prec:
        for fp in glob.glob(str(deal / "precedents" / "*.txt")): prec |= set(presented(read(fp)))
    prec &= set(ANALYSES); eligible = [k for k in book if k in prec]; outside = [k for k in book if k not in prec]
    out["book_analyses"] = {k: da[k] for k in book}; out["precedents_present"] = sorted(prec); out["eligible"] = eligible; out["outside_precedents"] = outside
    out["presented"] = [k for k in book if pres[k]]; out["missing"] = [k for k in eligible if not pres[k]]; out["outside_precedents_presented"] = [k for k in outside if pres[k]]
    out["coverage"] = round(sum(1 for k in eligible if pres[k]) / len(eligible), 2) if eligible else None
    out["coverage_book"] = round(sum(1 for k in book if pres[k]) / len(book), 2) if book else None; out["coverage_core"] = round(sum(1 for k in core if pres[k]) / len(core), 2) if core else None
    # reference items carried as tables, and sensitivity grids: filed sections state these in a sentence or as a range
    AX = re.compile(r"^\(?-?\d+(\.\d+)?\s?(%|x)\)?$", re.I); lines = draft.split("\n"); ref_tabs, grids, i = [], 0, 0
    while i < len(lines):
        if lines[i].strip().startswith("|"):
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"): j += 1
            rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in lines[i:j] if not re.match(r"^\|(\s*:?-+:?\s*\|)+\s*$", l.strip())]
            ctx = "\n".join(lines[max(0, i - 6):i])
            for k in ("trading_range", "targets"):
                if k in da and re.search(ANALYSES[k], ctx, re.I): ref_tabs.append(k)
            if len(rows) >= 3 and sum(1 for c in rows[0][1:] if AX.match(c)) >= 2 and sum(1 for r in rows[1:] if r and AX.match(r[0])) >= 2: grids += 1
            i = j
        else: i += 1
    out["reference_items_as_tables"] = sorted(set(ref_tabs)); out["sensitivity_grids"] = grids
    gl = json.load(open(deal / "defined_terms.json"))["terms"] if (deal / "defined_terms.json").exists() else []; used, incons = [], []
    for t in gl:
        term = t["term"]
        if len(term) < 3 or not term[0].isupper(): continue
        exact = len(re.findall(r"(?<![A-Za-z])" + re.escape(term) + r"(?![A-Za-z])", draft))
        if exact: used.append(term)
        other = (len(re.findall(r"(?<![A-Za-z])" + re.escape(term) + r"(?![A-Za-z])", draft, re.I)) - exact) if " " in term else len(re.findall(r"\bthe " + re.escape(term.lower()) + r"(?![A-Za-z])", draft))
        if other: incons.append({"term": term, "other_form_uses": other})
    out["glossary_present"] = bool(gl); out["glossary_terms_used"] = len(used); out["defined_term_inconsistencies"] = sorted(incons, key=lambda x: -x["other_form_uses"])[:25]
    peers = []
    for tb in tables(draft):
        head = " ".join(tb[0]).lower()
        if len(tb) >= 4 and re.search(r"compan|peer|selected", head) and not re.search(r"target|acquir|announc|date", head):
            peers = [r[0] for r in tb[1:] if r and r[0] and not re.match(r"^(mean|median|min|max|minimum|maximum|high|low|average|overall|total|\d)", r[0], re.I)]; break
    out["peer_names"] = len(peers); out["peer_names_with_legal_suffix"] = sum(1 for p in peers if LEGAL.search(p)); out["peer_names_without_suffix"] = [p for p in peers if not LEGAL.search(p)][:20]
    inputs = "\n".join([deck, ocr, letter, json.dumps(facts), json.dumps(gl), read(deal / "inputs" / "engagement_letter.txt"), read(deal / "inputs" / "relationship_memo.txt")])
    normn = lambda s: s.replace("$", "").replace(",", "").rstrip("x%").strip(); have = {normn(m) for m in re.findall(r"\$?\d[\d,]*(?:\.\d+)?", inputs)}
    cand = [n for n in re.findall(r"\$?\d[\d,]*(?:\.\d+)?[x%]?", draft) if not re.fullmatch(r"(19|20)\d\d", normn(n)) and not (normn(n).isdigit() and int(normn(n)) <= 31)]
    miss = [n for n in cand if normn(n) not in have]; out["numbers_checked"] = len(cand); out["numbers_not_in_inputs"] = len(miss); out["numbers_not_in_inputs_examples"] = sorted(set(miss))[:20]
    sents = re.split(r"(?<=[.!?])\s+", draft); out["commentary_sentences"] = [s[:120] for s in sents if META.search(s)][:10]; out["markers_left"] = bool(MARK.search(draft)); out["reviewer_markers"] = REVIEWER.findall(draft)[:20]
    out["tables_present"] = len(tables(draft)) >= 2
    rat = json.load(open(deal / "shell" / "rationale.json")) if (deal / "shell" / "rationale.json").exists() else {}; base = rat.get("selected"); bl = len(read(deal / "precedents" / f"{base}.txt")) if base else 0
    out["base"] = base; out["length_ratio_vs_base"] = round(len(draft) / bl, 2) if bl else None; out["length_ratio_vs_shell"] = round(len(draft) / len(comp), 2) if comp else None
    (deal / "draft").mkdir(exist_ok=True); json.dump(out, open(deal / "draft" / "selfscore.json", "w"), indent=1)
    print(json.dumps(out, indent=1))
    print("\nSUMMARY  advisor language %s | letter carry-over %s | shell retention %s | analyses the precedents present, presented %s (missing: %s; outside the precedents but presented: %s; reference items as tables: %s; sensitivity grids: %d) | glossary terms used %d%s, written in another form: %d | peer names with legal suffix %d/%d | numbers not in inputs %d/%d | commentary %d | markers %s | reviewer markers %d | tables %s | length vs base %s"
          % (out["advisor_language_share"], out["letter_carry_over"], out["composite_retention"], out["coverage"], ",".join(out["missing"]) or "none", ",".join(out["outside_precedents_presented"]) or "none", ",".join(out["reference_items_as_tables"]) or "none", out["sensitivity_grids"], out["glossary_terms_used"], "" if gl else " (no glossary)", len(incons), out["peer_names_with_legal_suffix"], out["peer_names"], out["numbers_not_in_inputs"], out["numbers_checked"], len(out["commentary_sentences"]), out["markers_left"], len(out["reviewer_markers"]), out["tables_present"], out["length_ratio_vs_base"]))
if __name__ == "__main__": main()
