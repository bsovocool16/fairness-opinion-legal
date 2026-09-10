#!/usr/bin/env python3
"""The whole path end to end on the bundled public deal (Distribution Solutions Group 2026, William Blair, Rule 13e-3).
  python3 demo.py walk [<run dir>] [--stage intake|search|shell|draft|redline|filed|all]   replay a completed run as markdown
  python3 demo.py setup-live <deals dir> [--code demo-dsgr-2026] [--model opus|fable]      fresh deal folder from the example inputs, intake done
  python3 demo.py filed <deal dir>                                                          redline the deal's draft against the section as filed
The default run dir is examples/distribution-solutions-2026/run in the plugin. Writes nothing in walk mode."""
import sys, json, re, argparse, shutil, subprocess, datetime
from pathlib import Path
HERE = Path(__file__).resolve().parent; PLUGIN = HERE.parent
EX = PLUGIN / "examples" / "distribution-solutions-2026"; RUN = EX / "run"
sys.path.insert(0, str(HERE / "redline"))
LABEL = {"comps": "selected public companies", "precedents": "selected precedent transactions", "dcf": "discounted cash flow", "lbo": "leveraged buyout",
         "premiums": "premiums paid", "trading_range": "52-week trading range", "targets": "analyst price targets", "sotp": "sum of the parts",
         "future_price": "illustrative future share price", "sensitivity": "sensitivity tables"}
def words(p): return len(p.read_text(errors="ignore").split()) if p.exists() else 0
def pages(p): return p.read_text(errors="ignore").count("-----PAGE-----") + 1 if p.exists() and p.stat().st_size else 0
def kb(p): return f"{p.stat().st_size / 1024:.0f} KB"
def ranges(nums):
    nums = sorted(set(nums)); out = []
    for n in nums:
        if out and n == out[-1][1] + 1: out[-1][1] = n
        else: out.append([n, n])
    return ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in out)
def table(head, rows):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])
def stats(orig, rev):
    import redline as RL
    O, _ = RL.split_paragraphs(orig, "auto"); R, _ = RL.split_paragraphs(rev, "auto"); paras, al = RL.diff_aligned(O, R)
    n = lambda kinds: sum(len(t.split()) for p in paras for k, t in p if k in kinds)
    return {"original_words": sum(len(p) for p in O), "revised_words": sum(len(p) for p in R), "unchanged": n(("eq", "mv")), "deleted": n(("del",)), "inserted": n(("ins",)), **al}
def facts_lines(f):
    reg = "Rule 13e-3 going-private" if str(f.get("regime", "")).startswith("13e") else "conventional"
    price = f.get("offer_price"); cons = f.get("consideration", "")
    L = [f"- Regime: {reg} (asked first at intake, never inferred)",
         f"- Target: {f.get('target', '')} ({f.get('ticker', '')}) · Buyer: {f.get('buyer', '')} ({f.get('buyer_type', '')})",
         f"- Consideration: ${price:,.2f} per share in {cons}" if isinstance(price, (int, float)) else f"- Consideration: {cons}",
         f"- Advisor: {f.get('advisor', '')}, {f.get('role', '')}; addressee {f.get('addressee', '')}; opinion dated {f.get('opinion_date', '')}, pricing as of {f.get('pricing_date', '')}"]
    el = f.get("engagement_letter") or {}
    if el.get("fee_note"): L.append(f"- Fee terms given at intake: {el['fee_note']}")
    return L
def stage_intake(run):
    f = json.load(open(run / "facts.json")); da = json.load(open(run / "deck_analyses.json")); det = da.get("detail", {})
    book = run / "inputs" / "book.txt"; ocr = run / "inputs" / "book_ocr.txt"; letter = run / "inputs" / "opinion_letter.txt"
    ocr_pages = sorted({p for d in det.values() for p in d.get("pages_ocr", [])})
    L = ["## 1. Intake: what was uploaded and confirmed",
         f"- Board book: {pages(book)} pages ({words(book)} words of text layer; OCR read {pages(ocr) or len(ocr_pages)} pages, {words(ocr)} words) · Opinion letter: {words(letter)} words"] + facts_lines(f)
    rows = [(LABEL.get(k, k), v, ranges(det.get(k, {}).get("pages_text_layer", []) + det.get(k, {}).get("pages_ocr", [])) or "") for k, v in da["deck_analyses"].items()]
    L += ["", "Analyses the book presents (read by the classifier, confirmed at the intake gate):", "", table(["analysis", "status", "pages"], rows)]
    return "\n".join(L)
def stage_search(run):
    log = (run / "search.log").read_text(errors="ignore").splitlines() if (run / "search.log").exists() else []
    idx = json.load(open(run / "precedents" / "INDEX.json"))
    L = ["## 2. Precedent search on EDGAR"]
    if log: L.append(f"- {log[0].strip()}; {sum(1 for l in log if 'verified' in l)} filings fetched and verified to carry the advisor's section; {len(idx)} kept that present analyses")
    rows = [(i + 1, e["name"].split("  (")[0].title(), e["date"], e["form"], e["regime"], ", ".join(LABEL.get(a, a) for a in e["presented"]), f"{e['coverage']:.2f}") for i, e in enumerate(idx)]
    L += ["", table(["rank", "filing", "filed", "form", "regime", "analyses presented", "coverage of the book"], rows), "", "Ranked by coverage of the book's analyses, with a bonus for the same regime, then recency. The gate here: approve the set, add or drop filings."]
    return "\n".join(L)
def stage_shell(run):
    rat = json.load(open(run / "shell" / "rationale.json")); prov = json.load(open(run / "shell" / "provenance.json")) if (run / "shell" / "provenance.json").exists() else {}
    sel = rat.get("selected"); cands = rat.get("candidates", []); name = next((c["name"].split("  (")[0].title() for c in cands if c["id"] == sel), sel)
    L = ["## 3. Shell", f"- Base: {name} ({sel}), score {next((c['score'] for c in cands if c['id'] == sel), '')}", f"- Rule: {rat.get('rule', '')}"]
    L += ["", table(["score", "candidate", "filed", "regime", "analyses"], [(c["score"], c["name"].split("  (")[0].title(), c["date"], c["regime"], ", ".join(LABEL.get(a, a) for a in c["analyses"]) or "none read") for c in cands])]
    segs = prov.get("segments", []); base = prov.get("base")
    if segs:
        srcs = {s["source"] for s in segs if s.get("source")}
        borrowed = [s for s in segs if s.get("source") and s["source"] != base]; uncovered = [s for s in segs if not s.get("source")]
        line = f"- Segments: {len(segs)} from {len(srcs)} filing(s)"
        line += ("; borrowed from another section by this advisor: " + ", ".join(f"{LABEL.get(s['label'], s['label'])} ({s['source']})" for s in borrowed)) if borrowed else "; nothing borrowed"
        if uncovered: line += "; in the book but in none of the precedents, so marked in the shell for the drafter to write in the advisor's form: " + ", ".join(LABEL.get(s["label"], s["label"]) for s in uncovered)
        L += ["", line]
    for n in ["shell_suggested.txt", "shell_composite.txt", "shell_composite_eligible.txt"]:
        if (run / "shell" / n).exists(): L.append(f"- shell/{n}: {words(run / 'shell' / n)} words")
    return "\n".join(L)
def stage_draft(run):
    ss = json.load(open(run / "draft" / "selfscore.json")) if (run / "draft" / "selfscore.json").exists() else {}
    sec = (run / "draft" / "section.txt").read_text(errors="ignore"); log = (run / "draft" / "log.md").read_text(errors="ignore") if (run / "draft" / "log.md").exists() else ""
    who = re.search(r"(?im)^Drafter:\s*(.+)$", log); model = who.group(1).strip() if who else ("Opus, objective mode" if "Opus" in (run / "deal.md").read_text(errors="ignore") else "see the log")
    L = ["## 4. Draft", f"- Drafter: {model}; {ss.get('draft_words', len(sec.split()))} words, {ss.get('length_vs_base', '')}x the base" if ss.get("length_vs_base") else f"- Drafter: {model}; {len(sec.split())} words"]
    rows = [("advisor-language share (6-word phrases found in this advisor's filings)", ss.get("advisor_language_share")), ("letter carry-over", ss.get("letter_carry_over")), ("shell retention", ss.get("composite_retention")),
            ("book analyses presented", f"{len(ss.get('presented', []))} of {len(ss.get('book_analyses', {}))}" + (f" (missing: {', '.join(ss['missing'])})" if ss.get("missing") else "")),
            ("selected companies by full legal name", f"{ss.get('peer_names_with_legal_suffix')} of {ss.get('peer_names')}"), ("numbers not found in the inputs", f"{ss.get('numbers_not_in_inputs')} of {ss.get('numbers_checked')} checked"),
            ("commentary, placeholders or markers in the text", "none" if not ss.get("commentary_sentences") and not ss.get("markers_left") else "yes"), ("reviewer items in the log", len(ss.get("reviewer_markers", [])))]
    L += ["", table(["self-score", "value"], [(a, b) for a, b in rows if b is not None])]
    first = next((p.strip() for p in re.split(r"\n\s*\n", sec) if len(p.split()) > 40), "")
    L += ["", "Opening paragraph:", "", "> " + first[:600] + ("…" if len(first) > 600 else "")]
    m = re.search(r"(?is)(facts? not available[^\n]*\n)(.*?)(?:\n#|\n\n[A-Z\[]|\Z)", log)
    if m and m.group(2).strip(): L += ["", "Facts the inputs lacked, omitted and logged:", "", "\n".join(l for l in m.group(2).strip().splitlines()[:8])]
    return "\n".join(L)
def stage_redline(run):
    shell = run / "shell" / "shell_composite_eligible.txt"
    if not shell.exists(): shell = run / "shell" / "shell_suggested.txt"
    st = stats(shell.read_text(errors="ignore"), (run / "draft" / "section.txt").read_text(errors="ignore"))
    L = ["## 5. Clean draft and redline against the shell", f"- Of the shell's {st['original_words']:,} words, {st['unchanged']:,} survive unchanged; {st['deleted']:,} struck (the base deal's facts and analyses the book lacks), {st['inserted']:,} inserted (this deal's facts, tables and results); {st['aligned']} paragraphs aligned, {st['moved']} moved"]
    for n in ["section.docx", "section.txt", "redline_vs_shell.docx", "redline_vs_shell.pdf"]:
        if (run / "redline" / n).exists(): L.append(f"- redline/{n} ({kb(run / 'redline' / n)})")
    L.append("- The gate here: reviewer sign-off. Nothing leaves the deal folder until then.")
    return "\n".join(L)
def stage_filed(run):
    filed = run / "filed" / "section_as_filed.txt"
    if not filed.exists(): return "## 6. Against the section as filed\n- not available for this deal"
    st = stats(filed.read_text(errors="ignore"), (run / "draft" / "section.txt").read_text(errors="ignore"))
    L = ["## 6. Against the section William Blair actually filed", "The drafter never saw it. Comparing afterwards:",
         f"- {st['unchanged']:,} of the filed section's {st['original_words']:,} words appear unchanged in the draft; {st['aligned']} of its {st['original_paragraphs']} paragraphs align with a draft paragraph",
         f"- {st['inserted']:,} draft words are not in the filing (mostly the proxy's defined terms, which the drafter cannot know without the draft proxy, and fuller tables); {st['deleted']:,} filed words are not in the draft"]
    for n in ["redline_vs_filed.docx", "redline_vs_filed.pdf"]:
        if (run / "filed" / n).exists(): L.append(f"- filed/{n} ({kb(run / 'filed' / n)})")
    return "\n".join(L)
STAGES = [("intake", stage_intake), ("search", stage_search), ("shell", stage_shell), ("draft", stage_draft), ("redline", stage_redline), ("filed", stage_filed)]
def walk(run, stage):
    f = json.load(open(run / "facts.json"))
    status = next((l.split(":", 1)[1].strip() for l in (run / "deal.md").read_text(errors="ignore").splitlines() if l.startswith("- Status:")), "") if (run / "deal.md").exists() else ""
    head = [f"# {f.get('target', '')} · {f.get('advisor', '')}", status, ""]
    out = [l for l in head if l is not None]
    for name, fn in STAGES:
        if stage in ("all", name): out += [fn(run), ""]
    if stage == "all":
        out += ["## Files", "", "\n".join(f"- {p.relative_to(run)} ({kb(p)})" for p in sorted(run.rglob("*")) if p.is_file() and p.suffix in (".docx", ".pdf", ".txt", ".json", ".md") and "precedents/" not in str(p.relative_to(run)))]
        out += [f"- precedents/: {len(list((run / 'precedents').glob('*.txt')))} filed sections as text, INDEX.json"]
    print("\n".join(out))
def setup_live(deals, code, model):
    deal = Path(deals).expanduser() / code
    if deal.exists(): sys.exit(f"{deal} exists; pick another --code or close that deal")
    (deal / "inputs").mkdir(parents=True)
    shutil.copy(EX / "board_book.pdf", deal / "inputs" / "book.pdf"); shutil.copy(EX / "opinion_letter.txt", deal / "inputs" / "opinion_letter.txt")
    f = json.load(open(RUN / "facts.json")); f["deck_source"] = {"file": "inputs/book.pdf", "pages": 32, "note": "exhibit (c)(viii) to the Schedule 13E-3, slide images without a text layer"}
    json.dump(f, open(deal / "facts.json", "w"), indent=1)
    today = datetime.date.today().isoformat()
    (deal / "deal.md").write_text(f"# {code}\n\n- Target: {f['target']} ({f['ticker']})\n- Buyer: {f['buyer']} ({f['buyer_type']})\n- Advisor: {f['advisor']}, {f['role']}\n- Regime: Rule 13e-3 going-private\n- Consideration: ${f['offer_price']:,.2f} in cash per share; opinion dated {f['opinion_date']}\n- Drafter model: {model}\n- Status: live demo opened {today}; intake answers taken from the bundled example\n- Confidentiality: none, public EDGAR material\n")
    (deal / "history.md").write_text(f"# history\n\n- {today} demo --live: folder created from the bundled example; intake answers from its README; regime 13e-3 confirmed; book and letter copied to inputs/\n")
    print(json.dumps({"deal": str(deal), "model": model, "next": ["extract the book with --ocr (inputs/book.pdf has no text layer)", "classify the book's analyses", "precedent-search", "shell-builder", "section-draft", "redline", "demo.py filed <deal>"]}, indent=1))
def filed(deal):
    deal = Path(deal); draft = deal / "draft" / "section.txt"
    if not draft.exists(): sys.exit("no draft/section.txt yet")
    (deal / "filed").mkdir(exist_ok=True); src = RUN / "filed" / "section_as_filed.txt"; dst = deal / "filed" / "section_as_filed.txt"
    if not dst.exists(): shutil.copy(src, dst)
    r = subprocess.run([sys.executable, str(HERE / "redline" / "redline.py"), str(dst), str(draft), str(deal / "filed" / "redline_vs_filed.docx"), "--pdf", "--title", "The draft compared with the section as filed (Distribution Solutions Group, 2026)", "--label-original", "section as filed", "--label-revised", "draft"], capture_output=True, text=True)
    st = stats(dst.read_text(errors="ignore"), draft.read_text(errors="ignore")); st["docx"] = (deal / "filed" / "redline_vs_filed.docx").exists(); st["pdf"] = (deal / "filed" / "redline_vs_filed.pdf").exists()
    if r.returncode: st["render_error"] = (r.stderr or r.stdout).strip()[-300:]
    print(json.dumps(st, indent=1))
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("walk"); w.add_argument("run", nargs="?", default=str(RUN)); w.add_argument("--stage", default="all", choices=["all"] + [s for s, _ in STAGES])
    s = sub.add_parser("setup-live"); s.add_argument("deals"); s.add_argument("--code", default="demo-dsgr-2026"); s.add_argument("--model", default="opus", choices=["opus", "fable"])
    f = sub.add_parser("filed"); f.add_argument("deal")
    a = ap.parse_args()
    if a.cmd == "walk": walk(Path(a.run), a.stage)
    elif a.cmd == "setup-live": setup_live(a.deals, a.code, a.model)
    else: filed(a.deal)
