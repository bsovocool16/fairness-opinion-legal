#!/usr/bin/env python3
"""Litera-style comparison of a revised document against an original, written as a .docx (optionally also a PDF).

  python redline.py ORIGINAL REVISED OUT.docx [--title T] [--pdf] [--reflow auto|on|off] [--threshold 0.35] [--json SPEC]

Inputs: .txt and .md are read as is; .docx through python-docx (falls back to pandoc); .pdf through pdftotext; .doc, .rtf
and .odt are converted with LibreOffice first. Marks in the output: text in REVISED that is not in ORIGINAL in blue double
underline, text in ORIGINAL that REVISED dropped in red strikethrough, paragraphs REVISED carries in a different position
in green, a bar in the left margin beside every altered paragraph, and a list of ORIGINAL paragraphs that REVISED does not
carry at the end. Comparison is by paragraph (aligned by word similarity), then by word, then by character inside short
replacements, so "paragraphs 2, 3 and 5" against "paragraphs 3, 4 and 6" marks the digits, not the sentence."""
import sys, re, json, difflib, argparse, subprocess, shutil, os, tempfile, bisect
from pathlib import Path
HERE = Path(__file__).resolve().parent
RENDER = HERE / "render_redline.js"

# ---------------------------------------------------------------- reading inputs
def find_soffice():
    for c in (os.environ.get("SOFFICE"), shutil.which("soffice"), "/Applications/LibreOffice.app/Contents/MacOS/soffice"):
        if c and Path(c).exists(): return c
    return None
def read_docx(p):
    try:
        import docx
        from docx.table import Table
        from docx.text.paragraph import Paragraph
    except ImportError:
        if shutil.which("pandoc"):
            r = subprocess.run(["pandoc", "-t", "plain", "--wrap=none", str(p)], capture_output=True, text=True)
            if r.returncode == 0: return r.stdout
        sys.exit("reading .docx needs python-docx (pip install python-docx) or pandoc on PATH")
    d = docx.Document(str(p)); parts = []
    for child in d.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p": parts.append(Paragraph(child, d).text)
        elif tag == "tbl":
            for row in Table(child, d).rows:
                seen, cells = [], []
                for c in row.cells:                      # a merged cell comes back once per grid column; keep it once
                    if any(c._tc is t for t in seen): continue
                    seen.append(c._tc); cells.append(" ".join(c.text.split()))
                parts.append("| " + " | ".join(cells) + " |")
    return "\n".join(parts)
def read_html(p):
    """Paragraphs in document order; every table row becomes a | cell | cell | line (currency, percent and parenthesis
    fragments that EDGAR puts in their own cells are glued back onto the number)."""
    try:
        from bs4 import BeautifulSoup, NavigableString, Tag
    except ImportError:
        if shutil.which("pandoc"):
            r = subprocess.run(["pandoc", "-t", "plain", "--wrap=none", str(p)], capture_output=True, text=True)
            if r.returncode == 0: return r.stdout
        sys.exit("reading .html needs beautifulsoup4 (pip install beautifulsoup4 lxml) or pandoc on PATH")
    raw = p.read_bytes()
    try: soup = BeautifulSoup(raw, "lxml")
    except Exception: soup = BeautifulSoup(raw, "html.parser")
    BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "ul", "ol", "br", "hr", "center", "blockquote", "pre", "section", "article", "header", "footer", "tr", "td", "th"}
    items = []
    def rows_of(tbl):
        rows = []
        for tr in tbl.find_all("tr"):
            out = []
            for td in tr.find_all(["td", "th"]):
                c = " ".join(td.get_text(" ").split())
                if not c: continue
                if out and (out[-1] in ("$", "€", "£", "(", "($", "-$") or c in (")", "%", ")%", "%)", "x")): out[-1] += c
                elif out and c.startswith((")", "%")): out[-1] += c
                else: out.append(c)
            if out: rows.append(out)
        return rows
    def walk(node):
        for ch in node.children:
            if isinstance(ch, NavigableString):
                t = " ".join(str(ch).split())
                if t and type(ch).__name__ not in ("Comment", "Doctype"): items.append(("t", t))
            elif isinstance(ch, Tag):
                if ch.name in ("script", "style", "head", "title"): continue
                if ch.name == "table":
                    items.append(("b", None))
                    for r in rows_of(ch): items.append(("r", "| " + " | ".join(r) + " |"))
                    items.append(("b", None))
                elif ch.name in BLOCK: items.append(("b", None)); walk(ch); items.append(("b", None))
                else: walk(ch)
    walk(soup.body or soup)
    lines, cur = [], []
    for k, v in items:
        if k == "t": cur.append(v)
        else:
            if cur: lines.append(" ".join(cur)); cur = []
            if k == "r": lines.append(v)
    if cur: lines.append(" ".join(cur))
    return "\n".join(lines)
def read_pdf(p):
    if not shutil.which("pdftotext"): sys.exit("reading .pdf needs pdftotext (poppler) on PATH")
    return subprocess.run(["pdftotext", str(p), "-"], capture_output=True, text=True).stdout
def read_input(path):
    p = Path(path); ext = p.suffix.lower()
    if ext == ".docx": return read_docx(p)
    if ext == ".pdf": return read_pdf(p)
    if ext in (".htm", ".html", ".xhtml"): return read_html(p)
    if ext in (".doc", ".rtf", ".odt", ".wpd"):
        so = find_soffice()
        if not so: sys.exit(f"reading {ext} needs LibreOffice (soffice on PATH, or set SOFFICE to its path)")
        with tempfile.TemporaryDirectory() as td:
            subprocess.run([so, "--headless", "--convert-to", "docx", "--outdir", td, str(p)], capture_output=True, text=True)
            conv = Path(td) / (p.stem + ".docx")
            if not conv.exists(): sys.exit(f"LibreOffice could not convert {p}")
            return read_docx(conv)
    return p.read_text(errors="ignore")

# ---------------------------------------------------------------- paragraphs
ZW = re.compile("[​­﻿]")
FURNITURE = re.compile(r"^\s*(?:-----PAGE-----|\d{1,3}|page \d{1,3}(?: of \d{1,3})?|[ivxlc]{1,6}|[A-Z]{1,2}-\s?\d{1,3})\s*$", re.I)
SENT_END = re.compile(r"[.:;!?\"”’)\]]\s*$")
STOPWORDS = {"of", "the", "and", "or", "to", "in", "by", "for", "with", "at", "a", "an", "on", "as", "its", "from", "that"}
CELL = re.compile(r"^(?:[\$€£]?\(?-?\d[\d,.]*\)?%?x?|n\.?m\.?|n\.?a\.?|NM|NA|Low|High|Mean|Median|Average|Company|Companies|Target|Acquirer|Acquiror|Date|Announced|Multiple|Multiples|Enterprise Value|Equity Value|EV|TEV|LTM|NTM|CY\d{2,4}[EA]?|FY\d{2,4}[EA]?|\d{4}[EA]?|Revenue|EBITDA|EBIT|EPS|P/E|EV\s*/\s*EBITDA)\b.{0,30}$", re.I)
def is_heading(line):
    w = line.split()
    if not (1 <= len(w) <= 12) or len(line) > 70 or line.endswith((",", ";")) or w[-1].lower() in STOPWORDS: return False
    caps = sum(1 for x in w if x[0].isupper() or x.lower() in STOPWORDS)
    return (caps / len(w) >= 0.75 and not SENT_END.search(line)) or line.isupper()
def is_cell(s): return len(s) <= 44 and (bool(re.search(r"\d", s)) or CELL.match(s) is not None) and not SENT_END.search(s)
def reflow(text):
    """Join hard-wrapped lines into paragraphs. A line continues the previous one unless the previous line ended a sentence or
    looks like a heading, or either line looks like a table cell. Page furniture (bare page numbers) is dropped."""
    lines = [ZW.sub("", l).strip() for l in text.split("\n")]
    lines = [l for l in lines if l and not FURNITURE.match(l)]
    out, cur = [], ""
    for s in lines:
        if not cur: cur = s; continue
        if is_cell(s) or is_cell(cur): out.append(cur); cur = s; continue
        prev_ends = bool(SENT_END.search(cur)); heading = is_heading(cur)
        cont = s[0].islower() or s[0] in ",;)”’" or (not prev_ends and not heading) or cur.endswith((",", "(", "“", " and", " or", " of", " the", " to", " in", " by", " for", " with", " at", " a", " an"))
        if cont and not (is_heading(s) and prev_ends): cur = cur + " " + s
        else: out.append(cur); cur = s
    if cur: out.append(cur)
    glued = []
    for p in out:
        if glued and (p in ("”", "—", "”.", ")") or len(p) < 4): glued[-1] += " " + p
        else: glued.append(p)
    return glued
def looks_hard_wrapped(text):
    ls = [l.strip() for l in text.split("\n") if l.strip() and not l.strip().startswith("|")]
    long = [l for l in ls if len(l) > 30]
    return len(long) >= 12 and sum(1 for l in long if not SENT_END.search(l)) / len(long) > 0.5
def normalize(para):
    para = re.sub(r"\s+", " ", para).strip()
    para = re.sub(r"^[•·\-—–•●]+\s*", "• ", para)                                  # one bullet glyph for every list marker
    para = para.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')      # straight quotes, so quote style is not a change
    if para.startswith("|"): para = re.sub(r"\s*\|\s*", " | ", para).strip()
    return para
def split_paragraphs(text, mode):
    """List of word lists, one per paragraph. mode: 'on' joins hard-wrapped lines, 'off' takes every non-blank line as a paragraph,
    'auto' picks by how many long lines end without sentence punctuation. Pipe-delimited table rows always stay one row each."""
    if mode == "auto": mode = "on" if looks_hard_wrapped(text) else "off"
    out, chunk = [], []
    def flush():
        if chunk: out.extend(reflow("\n".join(chunk)) if mode == "on" else [l for l in (ZW.sub("", x).strip() for x in chunk) if l]); chunk.clear()
    for line in text.split("\n"):
        if line.strip().startswith("|"): flush(); out.append(line.strip())
        else: chunk.append(line)
    flush()
    paras = [normalize(p) for p in out]
    return [p.split(" ") for p in paras if p], mode

def cut_section(paras, start, end, name):
    """Keep the paragraphs from the last paragraph that is exactly `start` (a heading; the last occurrence skips the summary
    and table-of-contents copies that precede the real section in a proxy) up to the first paragraph after it that is
    exactly `end`. A heading that is not found leaves that side uncut, with a note on stderr."""
    norm = lambda t: re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()
    texts = [norm(" ".join(p)) for p in paras]; s, e = 0, len(paras)
    if start:
        idx = [i for i, t in enumerate(texts) if t == norm(start)]
        if idx: s = idx[-1]
        else: print(f"note: --from heading not found in {name}; using the whole document", file=sys.stderr)
    if end:
        idx = [i for i, t in enumerate(texts) if i > s and t == norm(end)]
        if idx: e = idx[0]
        else: print(f"note: --to heading not found in {name} after the start; running to the end", file=sys.stderr)
    return paras[s:e]

# ---------------------------------------------------------------- diff
def char_diff(a_str, b_str):
    """Character-level runs for a replaced word; whole-word delete/insert when the two words are dissimilar."""
    sm = difflib.SequenceMatcher(None, a_str, b_str, autojunk=False)
    if sm.ratio() < 0.5: return [["del", a_str], ["ins", b_str]]
    runs = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal": runs.append(["eq", a_str[i1:i2]])
        elif op == "delete": runs.append(["del", a_str[i1:i2]])
        elif op == "insert": runs.append(["ins", b_str[j1:j2]])
        else: runs += [["del", a_str[i1:i2]], ["ins", b_str[j1:j2]]]
    return runs
def word_diff(a_words, b_words, moved=False):
    """Runs of [kind, text] with exact spacing: kinds eq, del, ins, and mv for unchanged text inside a moved paragraph."""
    runs = []; sm = difflib.SequenceMatcher(None, a_words, b_words, autojunk=False); keep = "mv" if moved else "eq"
    def add(kind, text):
        if not text: return
        if runs and runs[-1][0] == kind: runs[-1][1] += text
        else: runs.append([kind, text])
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal": add(keep, " ".join(a_words[i1:i2]) + " ")
        elif op == "delete": add("del", " ".join(a_words[i1:i2]) + " ")
        elif op == "insert": add("ins", " ".join(b_words[j1:j2]) + " ")
        else:
            aw, bw = a_words[i1:i2], b_words[j1:j2]
            if len(aw) == len(bw) and len(aw) <= 3:
                for x, y in zip(aw, bw):
                    for k, t in char_diff(x, y): add(keep if k == "eq" else k, t)
                    add(keep, " ")
            else: add("del", " ".join(aw) + " "); add("ins", " ".join(bw) + " ")
    return runs
def lis_indices(seq):
    """Positions of one longest strictly increasing subsequence: the aligned paragraphs that keep their relative order."""
    tails, tails_idx, prev = [], [], [-1] * len(seq)
    for k, v in enumerate(seq):
        pos = bisect.bisect_left(tails, v)
        if pos == len(tails): tails.append(v); tails_idx.append(k)
        else: tails[pos] = v; tails_idx[pos] = k
        prev[k] = tails_idx[pos - 1] if pos > 0 else -1
    out, k = [], (tails_idx[-1] if tails_idx else -1)
    while k != -1: out.append(k); k = prev[k]
    return set(out)
def diff_aligned(O, R, threshold=0.35):
    """Align revised paragraphs to original paragraphs by word similarity (best match first, each used once), diff inside each
    aligned pair, mark aligned paragraphs that break the original order as moved, show unmatched revised paragraphs as
    insertions where they stand, and list original paragraphs the revised document does not carry at the end."""
    cands = []
    for j, d in enumerate(R):
        for i, f in enumerate(O):
            if abs(len(f) - len(d)) > 4 * max(len(f), len(d)): continue
            sm = difflib.SequenceMatcher(None, f, d, autojunk=False)
            if sm.real_quick_ratio() < threshold or sm.quick_ratio() < threshold: continue
            r = sm.ratio()
            if r >= threshold: cands.append((r, i, j))
    cands.sort(reverse=True); used_o, used_r, align = set(), set(), {}
    for r, i, j in cands:
        if i in used_o or j in used_r: continue
        align[j] = i; used_o.add(i); used_r.add(j)
    order = [j for j in range(len(R)) if j in align]; seq = [align[j] for j in order]
    keep = lis_indices(seq); moved = {order[k] for k in range(len(order)) if k not in keep}
    paras = []
    for j, d in enumerate(R):
        if j in align: paras.append(word_diff(O[align[j]], d, moved=(j in moved)))
        else: paras.append([["ins", " ".join(d) + " "]])
    missing = [i for i in range(len(O)) if i not in used_o]
    if missing:
        paras.append([["head", "Original paragraphs not carried into the revised document (%d of %d)" % (len(missing), len(O))]])
        for i in missing: paras.append([["del", " ".join(O[i]) + " "]])
    return paras, {"original_paragraphs": len(O), "revised_paragraphs": len(R), "aligned": len(align), "moved": len(moved)}

# ---------------------------------------------------------------- output
def render(spec, out, pdf=False):
    if not shutil.which("node"): sys.exit("rendering needs node on PATH (then `npm install` in the tool directory)")
    if not (HERE / "node_modules" / "docx").exists(): sys.exit(f"run `npm install` in {HERE} first (installs the docx package)")
    tmp = Path(out).with_suffix(".spec.json"); json.dump(spec, open(tmp, "w"))
    r = subprocess.run(["node", str(RENDER), str(tmp), str(out)], capture_output=True, text=True); tmp.unlink(missing_ok=True)
    if r.returncode != 0: sys.exit(r.stderr.strip())
    print(r.stdout.strip())
    if pdf:
        so = find_soffice()
        if not so: sys.exit("--pdf needs LibreOffice (soffice on PATH, or set SOFFICE to its path)")
        subprocess.run([so, "--headless", "--convert-to", "pdf", "--outdir", str(Path(out).resolve().parent), str(Path(out).resolve())], capture_output=True, text=True)
        p = Path(out).with_suffix(".pdf"); print("wrote " + str(p) if p.exists() else "pdf conversion failed")
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("original"); ap.add_argument("revised"); ap.add_argument("out", help="output .docx")
    ap.add_argument("--title", default=None, help="heading of the comparison document")
    ap.add_argument("--label-original", default="original", help="how the legend names the original (e.g. 'section as filed')")
    ap.add_argument("--label-revised", default="revised", help="how the legend names the revised document (e.g. 'draft')")
    ap.add_argument("--pdf", action="store_true", help="also convert the .docx to PDF with LibreOffice")
    ap.add_argument("--reflow", choices=["auto", "on", "off"], default="auto", help="join hard-wrapped lines into paragraphs (default: detect)")
    ap.add_argument("--threshold", type=float, default=0.35, help="minimum word similarity for two paragraphs to count as the same paragraph")
    ap.add_argument("--json", default=None, help="also write the comparison spec (runs per paragraph and stats) to this path")
    ap.add_argument("--from", dest="start", default=None, metavar="HEADING", help="compare only from this heading (last exact occurrence) in each document")
    ap.add_argument("--to", dest="end", default=None, metavar="HEADING", help="stop at this heading (first exact occurrence after the start)")
    a = ap.parse_args()
    O, mo = split_paragraphs(read_input(a.original), a.reflow); R, mr = split_paragraphs(read_input(a.revised), a.reflow)
    if a.start or a.end: O = cut_section(O, a.start, a.end, a.original); R = cut_section(R, a.start, a.end, a.revised)
    paras, al = diff_aligned(O, R, a.threshold)
    words = lambda kinds: sum(len(r[1].split()) for p in paras for r in p if r[0] in kinds)
    stats = {"original_words": sum(len(p) for p in O), "revised_words": sum(len(p) for p in R), "unchanged": words(("eq", "mv")), "deleted": words(("del",)), "inserted": words(("ins",)), **al, "reflow": {"original": mo, "revised": mr}}
    spec = {"title": a.title or f"{Path(a.revised).name} compared with {Path(a.original).name}", "labels": {"original": a.label_original, "revised": a.label_revised}, "stats": stats, "paras": paras}
    if a.json: json.dump(spec, open(a.json, "w"), indent=0)
    render(spec, a.out, a.pdf); print(json.dumps(stats))
if __name__ == "__main__": main()
