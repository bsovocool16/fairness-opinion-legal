"""EDGAR client for the precedent search: the full-text search recipes ("sharp" = "opinion of <bank>" as the proxy's section
heading; "broad" = "very truly yours" near the bank name, as a person would search), the per-analysis sub-searches, filing
document fetch, HTML-to-text that keeps paragraphs and table rows, and the section test. Forms DEFM14A, DEFM14C, SC 14D9,
SC 13E3. Used by precedent_search.py, verify_candidates.py and search_deal.py; not a command-line tool. The contact identity
the SEC requires in every request comes from the practice profile through EDGAR_UA."""
import time, re, os, html
import requests
from pathlib import Path
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
VALUE = re.compile(r"^[\(\-–—]?\$?\(?\d[\d,]*(?:\.\d+)?\)?[%x]?\)?$|^n\.?m\.?$|^n\.?a\.?$|^[-–—]$", re.I)   # a value-like cell
PREFIX = {"$", "(", "$(", "($", "€", "£", "us$", "c$", "a$", "(us$", "(€"}
SUFFIX = re.compile(r"^(?:\)|%|%\)|\)%|x|x\)|\)x|\*+|pts|bps|\(\d{1,2}\)|\([a-z]\))$", re.I)
FOOTNOTE = re.compile(r"^(?:\(\d{1,2}\)|\([a-z]\)|\*+)$", re.I)
BULLET = re.compile(r"^(?:[•·●▪■\-–—]|\(?[ivx]{1,4}\)|\(?[a-z]\)|\d{1,2}\.)$", re.I)
def _cell_text(body):
    t = html.unescape(re.sub(r"<[^>]+>", " ", body)); t = re.sub("[\u200b\u200c\u200d\ufeff\u00ad]", "", t).replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()
def _glue(cells):
    """Currency and unit fragments back onto their values: $ | 273 -> $273; (0.7 | %) -> (0.7%); 9.1x | (3) -> 9.1x (3). Empty cells dropped."""
    out = []
    for c in cells:
        if not c: continue
        if out and SUFFIX.match(c) and not (out[-1].lower() in PREFIX):
            out[-1] = out[-1] + (" " if FOOTNOTE.match(c) or not re.search(r"[\d)]$", out[-1]) else "") + c; continue
        if out and out[-1].lower() in PREFIX: out[-1] = out[-1] + c; continue
        out.append(c)
    return out
def table_rows(tbl):
    """An EDGAR table as clean rows: spans expanded, spacer cells dropped, currency and unit fragments and footnote markers glued
    to their values, stacked header rows folded into one (a group label joins the first sub-column under it). A row with one
    cell, or a footnote marker and its text, is returned as a one-cell row (prose)."""
    grid = []
    for r in re.findall(r"(?is)<tr\b[^>]*>(.*?)</tr>", tbl):
        cells, pos = [], 0
        for attrs, body in re.findall(r"(?is)<t[dh]\b([^>]*)>(.*?)</t[dh]>", r):
            m = re.search(r'colspan\s*=\s*"?(\d+)', attrs, re.I); n = int(m.group(1)) if m else 1; t = _cell_text(body)
            if t: cells.append((pos, pos + n, t))
            pos += n
        if cells: grid.append(cells)
    if not grid: return []
    def is_header(cells): return not any(VALUE.match(t) for _, _, t in cells)
    nh = 0
    while nh < min(3, len(grid)) and is_header(grid[nh]): nh += 1
    if nh == len(grid): nh = 0                                   # a table with no value cells: keep every row as is
    data = [_glue([t for _, _, t in cells]) for cells in grid[nh:]]
    widths = [len(r) for r in data]; W = max(set(widths), key=widths.count) if widths else 0
    rows = []
    if nh >= 2:
        top, sub = grid[0], [t for _, _, t in grid[1]]
        if nh == 3: sub = _fold(grid[1], [t for _, _, t in grid[2]], W)
        rows.append(_fold(top, sub, W))
    elif nh == 1: rows.append([t for _, _, t in grid[0]])
    rows += data
    out = []
    for r in rows:
        if len(r) == 2 and (FOOTNOTE.match(r[0]) or BULLET.match(r[0])): r = [r[0] + " " + r[1]]   # footnote or bullet layout table: prose
        out.append(r)
    return out
def _fold(top, sub, W):
    """Two header rows into one. A top cell whose span covers sub cells is a group label: it joins the first of them. When the
    filing's grid does not line up, the trailing top cells are taken as the group labels over the trailing sub cells."""
    T = [(s, e, t) for s, e, t in top]; n_t, n_s = len(T), len(sub)
    if n_s == 0: return [t for _, _, t in T]
    if n_t == n_s and n_t == W: return [(a + " " + b).strip() for (_, _, a), b in zip(T, sub)]
    groups = {}; unmapped = False
    for k, (s, e, t) in enumerate(top):
        pass
    subpos = [(s, e, t) for s, e, t in (sub if sub and isinstance(sub[0], tuple) else [])]
    if subpos:
        for j, (s, e, t) in enumerate(subpos):
            k = next((k for k, (ts, te, _) in enumerate(T) if ts <= s < te), None)
            if k is None: unmapped = True; break
            groups.setdefault(k, []).append(j)
    if subpos and not unmapped and groups:
        out = []
        for k, (_, _, t) in enumerate(T):
            js = groups.get(k, [])
            if js: out.append((t + " " + subpos[js[0]][2]).strip()); out += [subpos[j][2] for j in js[1:]]
            else: out.append(t)
        return out
    subt = [x[2] if isinstance(x, tuple) else x for x in sub]
    overlap = n_t + n_s - W
    if overlap < 1 or overlap > n_t: return [t for _, _, t in T] + subt
    lead = [t for _, _, t in T[:n_t - overlap]]; labels = [t for _, _, t in T[n_t - overlap:]]
    per = max(1, n_s // overlap); out = list(lead)
    for g, lab in enumerate(labels):
        chunk = subt[g * per:(g + 1) * per] if g < overlap - 1 else subt[g * per:]
        if chunk: out.append((lab + " " + chunk[0]).strip()); out += chunk[1:]
        else: out.append(lab)
    return out
def html_to_text(h):
    """Filing HTML to text that keeps paragraphs (one per line) and table rows (| cell | cell |), tables cleaned by table_rows."""
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h)
    h = re.sub(r"(?is)<table\b[^>]*>(.*?)</table>", lambda m: "\n" + "\n".join("| " + " | ".join(r) + " |" for r in table_rows(m.group(1))) + "\n", h)
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
