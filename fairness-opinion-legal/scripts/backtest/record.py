"""The filed record of a held-out deal: fetched from EDGAR into <bt>/sealed/ and parsed into sealed/truth.json.

The blind run never reads anything under sealed/ (backtest.py audit checks it). Network calls are in fetch(); every parser
below takes text, so the tests run them on excerpts without the network.

  sealed/proxy.txt            the definitive proxy as text (table rows kept as | cell | cell |)
  sealed/section.txt          the "Opinion of <advisor>" section, cut by verify_candidates.section_of
  sealed/opinion_letter.txt   the advisor's letter, cut from the proxy's annex
  sealed/projections.txt      the management projections table and its footnotes
  sealed/book.txt             the advisor's final board book (the Schedule 13E-3 exhibit named in the deal spec)
  sealed/truth.json           what the scorer compares against: ranges, parameters, peers, projections, analyses
"""
import re, sys, json
from pathlib import Path
HERE = Path(__file__).resolve().parent; SCRIPTS = HERE.parent; sys.path.insert(0, str(SCRIPTS))
from analyses import HEAD, presented, DECK_RX, NUMERIC

NUM = r"\$?\s?\(?-?\d[\d,]*(?:\.\d+)?\)?"
def num(s):
    """'$1,123' -> 1123.0; '(5.5)' -> -5.5; anything else -> None."""
    if s is None: return None
    t = s.replace("$", "").replace(",", "").strip(); neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()").strip()
    try: v = float(t)
    except ValueError: return None
    return -v if neg else v

# ---- the opinion section ---------------------------------------------------------------------------------------------
HEADS = [h for h in HEAD if h[0] != "other"] + [("targets", r"^(?:equity research|wall street research|research analysts?(?: price targets?)?)$"), ("premiums", r"^(?:all-cash )?premi(?:a|ums)\b")] + [h for h in HEAD if h[0] == "other"]
def segments(section):
    """{analysis: text} by the section's own headings: a line that matches a HEAD pattern and is short enough to be a heading."""
    lines = section.split("\n"); cuts = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s or len(s) > 90 or s.startswith("|") or s.endswith((":", ".", ",", ";")): continue   # a heading carries no end punctuation
        for key, rx in HEADS:
            if re.search(rx, s, re.I): cuts.append((i, key)); break
    out = {}
    for n, (i, key) in enumerate(cuts):
        j = cuts[n + 1][0] if n + 1 < len(cuts) else len(lines)
        out[key] = (out[key] + "\n" if key in out else "") + "\n".join(lines[i:j])   # a heading repeated (a sub-heading) extends the segment
    return out

RANGE = re.compile(r"(?:implied|reference|indicated|illustrative)[^$]{0,260}?\$\s?(\d[\d,]*(?:\.\d+)?)\s*(?:to|-|–|and)\s*\$\s?(\d[\d,]*(?:\.\d+)?)", re.I | re.S)
PCT_RANGE = r"(\d+(?:\.\d+)?)\s?%\s*(?:to|-|–)\s*(\d+(?:\.\d+)?)\s?%"
X_RANGE = r"(\d+(?:\.\d+)?)\s?x\s*(?:to|-|–)\s*(\d+(?:\.\d+)?)\s?x"
def per_share_range(seg):
    m = RANGE.search(re.sub(r"rounded to the nearest \$\s?\d+(?:\.\d+)?", "rounded", seg, flags=re.I))
    if m: return {"low": num(m.group(1)), "high": num(m.group(2)), "quote": re.sub(r"\s+", " ", m.group(0))[-200:]}
    m = re.search(r"\$\s?(\d[\d,]*(?:\.\d+)?) per share to \$\s?(\d[\d,]*(?:\.\d+)?) per share", seg)
    if m: return {"low": num(m.group(1)), "high": num(m.group(2)), "quote": m.group(0)}
    for ln in seg.split("\n"):                     # a low / high table row
        cells = [c.strip() for c in ln.strip("|").split("|")] if ln.startswith("|") else []
        vals = [num(c) for c in cells[1:] if re.fullmatch(r"\$\s?\d[\d,]*(?:\.\d+)?", c)]
        if len(vals) == 2 and re.search(r"low", seg, re.I) and re.search(r"high", seg, re.I): return {"low": min(vals), "high": max(vals), "quote": ln}
    return None

def params(seg):
    """Discount rates, perpetuity growth rates, multiples applied, and the multiple statistics of the peer set, where stated."""
    p = {}
    m = re.search(r"discount rates?[^.%]{0,120}?" + PCT_RANGE, seg, re.I)
    if m: p["discount_rate"] = [float(m.group(1)) / 100, float(m.group(2)) / 100]
    m = re.search(r"perpetuity growth rates?[^.%]{0,80}?" + PCT_RANGE, seg, re.I)
    if m: p["perpetuity_growth"] = [float(m.group(1)) / 100, float(m.group(2)) / 100]
    m = re.search(r"(?:terminal|exit)[^.]{0,60}multiples?[^.]{0,80}?" + X_RANGE, seg, re.I)
    if m: p["exit_multiple"] = [float(m.group(1)), float(m.group(2))]
    m = re.search(r"(?:applied|selected)[^.]{0,80}?multiples?(?: reference)?(?: range)?(?: of)?\s*" + X_RANGE + r"([^.]{0,120})", seg, re.I)
    if m: p["multiple_applied"] = [float(m.group(1)), float(m.group(2))]; p["multiple_basis"] = re.sub(r"\s+", " ", m.group(3)).strip()
    m = re.search(r"range of premi(?:a|ums)[^.%]{0,40}?" + PCT_RANGE, seg, re.I)
    if m: p["premium"] = [float(m.group(1)) / 100, float(m.group(2)) / 100]
    m = re.search(r"low, high and median[^.]{0,160}?(\d+(?:\.\d+)?)x, (\d+(?:\.\d+)?)x,? and (\d+(?:\.\d+)?)x", seg, re.I)
    if m: p["peer_low_high_median"] = [float(m.group(i)) for i in (1, 2, 3)]
    return p

def table_names(seg):
    """First cells of the |table| rows in a segment that carry a number (the selected companies), headers dropped."""
    out = []
    for ln in seg.split("\n"):
        if not ln.startswith("|"): continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        figs = cells[1:]
        if len(cells) >= 2 and all(re.fullmatch(r"[\$\(\)\d.,x%\s–-]+|n/?a|nm|n\.m\.|—|-", c, re.I) for c in figs if c) and any(re.search(r"\d", c) for c in figs) and not re.search(r"\d", cells[0]): out.append(cells[0])
    return out

def dcf_method(seg):
    g = bool(re.search(r"perpetuity growth", seg, re.I)); x = bool(re.search(r"(?:terminal|exit) (?:value )?multiple|terminal (?:year )?(?:ebitda )?multiple", seg, re.I))
    return "both" if g and x else "pgr" if g else "exit" if x else None

def reference_only(seg):
    return bool(re.search(r"for reference (?:purposes )?only|for informational purposes|not (?:as )?(?:a )?(?:component|part) of|reference data", seg, re.I))

def parse_section(section):
    segs = segments(section); out = {"presented": presented(section), "analyses": {}}
    for key, seg in segs.items():
        if key == "other": continue
        rec = {"range": per_share_range(seg), "params": params(seg), "reference_only": reference_only(seg)}
        if key == "comps": rec["peers"] = table_names(seg)
        if key == "dcf": rec["method"] = dcf_method(seg)
        out["analyses"][key] = rec
    return out

# ---- the projections table -------------------------------------------------------------------------------------------
YEAR = re.compile(r"(?:Q\d\s?-\s?Q\d\s?)?(20\d\d)\s?[EAP]?")
def projections(proxy):
    """The management projections: the first |table| after a 'Projections' heading whose header row names future years.
    Returns {years, rows: {label: [values]}, ltm_adj_ebitda, text} or None."""
    lines = proxy.split("\n")
    starts = [i for i, ln in enumerate(lines) if re.search(r"(?:summary of (?:the )?(?:management )?projections|prospective financial information|financial projections|management projections|financial forecasts?)", ln, re.I) and len(ln) < 200]
    for i in starts:
        for j in range(i, min(i + 40, len(lines))):
            ln = lines[j]
            if not ln.startswith("|"): continue
            head = [c.strip() for c in ln.strip("|").split("|")]
            yrs = [YEAR.search(c.replace(" ", "")) or YEAR.search(c) for c in head[1:]]
            if sum(1 for y in yrs if y) < 3: continue
            years = [(("stub " if re.search(r"Q\d", c) else "") + y.group(1)) if y else c for c, y in zip(head[1:], yrs)]
            rows, k = {}, j + 1
            while k < len(lines) and lines[k].startswith("|"):
                cells = [c.strip() for c in lines[k].strip("|").split("|")]
                label = re.sub(r"\s*(?:\(\d\))+\s*$", "", cells[0]).strip()
                vals = [num(c) for c in cells[1:]]
                if any(v is not None for v in vals): rows[label] = vals
                k += 1
            notes = "\n".join(lines[k: k + 12])
            m = re.search(r"Last Twelve Months Adjusted EBITDA[^$]{0,80}\$\s?(\d[\d,]*(?:\.\d+)?)", notes, re.I)
            return {"years": years, "rows": rows, "ltm_adj_ebitda": num(m.group(1)) if m else None, "text": "\n".join(lines[i: k + 12])}
    return None

# ---- historical financials as the proxy summarizes them ---------------------------------------------------------------
HIST_ROWS = {"revenue": r"^(?:net sales|total net sales|net revenues?|total revenues?|revenues?|sales)$", "ebit": r"^(?:income \(loss\) from operations|\(loss\) income from operations|income from operations|operating income(?: \(loss\))?)$",
             "net_income": r"^(?:net income(?: \(loss\))?|net \(loss\) income)$",
             "net_income_parent": r"^net (?:income(?: \(loss\))?|\(loss\) income) attributable to (?:controlling interest|(?:the )?company|common (?:stock|share)holders|[A-Z][\w.,& ]{1,40}(?:inc\.?|corporation))$"}
def historicals(proxy):
    """Fiscal-year rows of the proxy's summary financial statements ('Summary Consolidated Statements of Operations' or
    'Selected Historical ...'): {fy: {revenue, ebit, net_income}}. Interim tables (three/six months) are skipped."""
    lines = proxy.split("\n"); out = {}
    for i, ln in enumerate(lines):
        if not re.search(r"(?:summary|selected) (?:historical )?(?:consolidated )?(?:statements? of operations|financial (?:data|information)|income statement)", ln, re.I) or len(ln) > 200: continue
        j = next((k for k in range(i + 1, min(i + 6, len(lines))) if lines[k].startswith("|")), None)
        if j is None: continue
        head = lines[j]
        if re.search(r"months ended", head, re.I): continue
        yrs = re.findall(r"(20\d\d)", head)
        if len(yrs) < 2: continue
        k = j + 1
        while k < len(lines) and lines[k].startswith("|"):
            cells = [c.strip() for c in lines[k].strip("|").split("|")]
            for key, rx in HIST_ROWS.items():
                if re.match(rx, cells[0], re.I):
                    vals = [num(c) for c in cells[1:]][: len(yrs)]
                    for y, v in zip(yrs, vals):
                        if v is not None: out.setdefault(int(y), {}).setdefault(key, v)
            k += 1
        if out: break
    return out

# ---- the opinion letter ----------------------------------------------------------------------------------------------
def letter(proxy, bank_phrases):
    """The advisor's letter: from the end of the annex before it to its signature block ('Very truly yours, <ADVISOR>')."""
    sig = None
    for m in re.finditer(r"very truly yours,?", proxy, re.I):
        if any(p.lower() in proxy[m.end(): m.end() + 200].lower() for p in bank_phrases): sig = m
    if not sig: return None
    end = sig.end() + 200; tail = proxy[sig.end(): end]
    am = re.search(r"Annex\s?([A-Z])\s?-\s?\d+", tail); letter_id = am.group(1) if am else None
    end = sig.end() + (am.start() if am else 160)
    start = None
    if letter_id and letter_id > "A":
        prev = list(re.finditer(rf"Annex\s?{chr(ord(letter_id) - 1)}\s?-\s?\d+(?:\s*Table of Contents)?", proxy[: sig.start()]))
        if prev: start = prev[-1].end()
    if start is None or sig.start() - start > 40000:
        hd = list(re.finditer(rf"(?m)^\s*(?:ANNEX|Annex)\s+{letter_id or '[A-Z]'}\s*$", proxy[: sig.start()]))
        start = hd[-1].end() if hd else max(0, sig.start() - 20000)
    txt = proxy[start:end]
    txt = re.sub(r"Annex\s?[A-Z]\s?-\s?\d+\s*(?:Table of Contents)?", "\n", txt)
    return txt.strip()

# ---- the board book --------------------------------------------------------------------------------------------------
def book_analyses(book):
    """Analyses the advisor's book shows with numbers, by the same title vocabulary the classifier uses."""
    out = []
    for key, rx in DECK_RX.items():
        if any(NUMERIC.search(book[m.end(): m.end() + 1500]) for m in re.finditer(rx, book, re.I)): out.append(key)
    return sorted(out)

def book_ranges(book):
    """Per-share ranges the book's summary (football field) states as '$x – $y' near an analysis name: {analysis: [(lo, hi)]}."""
    out = {}
    for key, rx in DECK_RX.items():
        for m in re.finditer(rx, book, re.I):
            r = re.search(r"\$\s?(\d+(?:\.\d+)?)\s*(?:–|-|to)\s*\$\s?(\d+(?:\.\d+)?)", book[m.end(): m.end() + 300])
            if r: out.setdefault(key, []).append((float(r.group(1)), float(r.group(2))))
    return out

# ---- assemble --------------------------------------------------------------------------------------------------------
def truth(spec, proxy, section, book):
    sec = parse_section(section or ""); pj = projections(proxy or "")
    return {"schema": "backtest_truth/1", "deal": spec["id"], "advisor": spec["advisor"], "offer_price": spec["offer_price"],
            "unaffected": spec.get("unaffected_price"), "section": sec, "historicals": historicals(proxy or ""), "manual": spec.get("truth", {}), "projections": {k: v for k, v in (pj or {}).items() if k != "text"} if pj else None,
            "book": {"analyses": book_analyses(book or ""), "ranges": book_ranges(book or "")} if book else None}

def fetch(spec, bt, log=print):
    """Fetch the filed record named in the deal spec into <bt>/sealed/ and write truth.json."""
    import edgar_precedents as EP
    from verify_candidates import section_of
    sealed = Path(bt) / "sealed"; sealed.mkdir(parents=True, exist_ok=True); rec = spec["record"]; cik = spec["cik"]
    proxy = EP.fetch_doc(cik, rec["proxy"]["acc"], rec["proxy"]["doc"])
    if not proxy: raise SystemExit(f"could not fetch the proxy {rec['proxy']}")
    (sealed / "proxy.txt").write_text(proxy); log(f"proxy: {len(proxy):,} chars")
    phrases = EP.BANK_PHRASES.get(spec["bank"], [spec["advisor"]])
    section = section_of(proxy, phrases) or ""
    (sealed / "section.txt").write_text(section); log(f"section: {len(section):,} chars")
    lt = letter(proxy, phrases) or ""
    (sealed / "opinion_letter.txt").write_text(lt); log(f"letter: {len(lt):,} chars")
    pj = projections(proxy)
    if pj: (sealed / "projections.txt").write_text(pj["text"]); log(f"projections: {', '.join(pj['rows'])} for {pj['years']}")
    book = ""
    if rec.get("book"):
        book = EP.fetch_doc(cik, rec["book"]["acc"], rec["book"]["doc"]); (sealed / "book.txt").write_text(book); log(f"book: {len(book):,} chars")
    t = truth(spec, proxy, section, book)
    (sealed / "truth.json").write_text(json.dumps(t, indent=1)); log(f"truth: analyses {sorted(t['section']['analyses'])}")
    return t
