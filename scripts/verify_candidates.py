"""Cut the advisor's opinion section out of a fetched filing and read the analyses it presents. Used by precedent_search."""
import re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import edgar_precedents as EP
from analyses import ANALYSES, NUMERIC, presented
def section_of(text, phrases):
    """The opinion section: among the occurrences of an "Opinion of <bank>" heading, the one followed by the most analysis
    vocabulary (a contents entry or an annex index has none), cut at the next major proxy heading."""
    t = re.sub(r"[ \t]+", " ", text); occ = {}
    def at_heading(i): return bool(re.search(r"(?:^|\n|\|\s*|[.:;”\")]\s*|\)\s+)$", t[max(0, i - 4): i])) and not re.search(r"\b(?:the|an|its|our|such)\s+$", t[max(0, i - 6): i], re.I)
    for ph in phrases:
        for m in re.finditer(r"opinion of (?:its |the |our )?(?:(?:special committee's |company's )?financial advisor[^.]{0,40})?" + re.escape(ph), t, re.I): occ[m.start()] = "a"
        for m in re.finditer(r"(?:summary of (?:the )?(?:material )?financial analyses of|financial analyses of|fairness opinion of|opinion and analyses of) " + re.escape(ph), t, re.I): occ[m.start()] = "b"
        for m in re.finditer(r"opinion of (?:[A-Z][\w&'’.,-]* ){0,6}(?:financial advisor|special committee's financial advisor)s?", t, re.I):   # "Opinion of Perspecta's Financial Advisor" followed by the bank
            if re.search(re.escape(ph), t[m.end(): m.end() + 400], re.I): occ[m.start()] = "c"
    if not occ: return None
    def score(i):
        w = t[i: i + 40000]; v = sum(len(re.findall(rx, w, re.I)) for rx in ANALYSES.values())
        if re.search(r"(?:was |were |has been |have been )?(?:retained|engaged) (?:by|to act|as|to render)|acted as (?:the |its |an? )?(?:exclusive )?financial advisor|to act as (?:its |the )?(?:exclusive )?financial advisor|pursuant to an engagement letter", t[i: i + 700], re.I): v += 10
        if at_heading(i): v += 6                        # a heading sits at a sentence boundary; a prose mention does not
        if occ[i] in ("b", "c"): v += 2
        return (v, -i)                                  # ties go to the earlier occurrence (the heading precedes the prose that cites it)
    best = max(occ, key=score); seg = t[best: best + 90000]
    END = re.compile(r"(?:Certain (?:Unaudited )?(?:Financial )?Projections|(?:Unaudited )?Prospective Financial Information|Financial Forecasts|Projected Financial Information|Management Projections|Summary of (?:the )?(?:Financial )?Projections|Interests of (?:the Company's |our |[A-Z][\w']* )?(?:Directors|Executive)|Financing of the|Regulatory Approvals|Material U\.S\. Federal Income Tax|Appraisal Rights|Delisting and Deregistration|Litigation Relat|Purposes? and Reasons|Position of the [A-Z][\w ]{2,40}(?:Filing Parties|Parties|Buyer|Purchaser|Parent)|Plans for [A-Z][\w]* (?:After|Following)|Certain Effects of the|Alternatives to the|Effects on the Company|Reasons for the (?:Merger|Transaction)|Recommendation of the (?:Board|Special Committee)|Opinion of [A-Z][\w.&, ]{2,60}(?:LLC|L\.L\.C\.|Inc\.|LP|Partners|Securities|Capital))", re.I)
    for m in END.finditer(seg, 6000):
        before, after = seg[max(0, m.start() - 60): m.start()], seg[m.end(): m.end() + 3]
        if re.search(r"caption|heading|entitled|see |section|titled|[“\"‘']\s*$", before, re.I) or re.match(r"\s*[”\"’']", after): continue   # a cross-reference, not the next heading
        if not (re.search(r"(?:^|\n|\|\s*|[.:;”\")]\s*|\)\s+)$", seg[max(0, m.start() - 4): m.start()]) and not re.search(r"\b(?:the|an|its|our|such|to|upon|on|in)\s+$", seg[max(0, m.start() - 6): m.start()], re.I)): continue   # mid-sentence mention
        if any(ph.lower() in m.group(0).lower() for ph in phrases): continue   # this advisor's own heading text inside its section
        return seg[: m.start()]
    return seg
def best_section(acc, phrases, hint_doc=None, max_docs=5):
    """Fetch the filing's documents in order (main document, proxy exhibits, others) and return the first opinion section that
    is long enough and presents an analysis, else the longest section found: (section, doc, form, text)."""
    docs = EP.filing_docs(acc); order = []
    for cik, doc, ft, form in docs:
        if cik and (doc, ) not in [(o[1],) for o in order]: order.append((cik, doc, ft, form))
    if hint_doc and docs: order.insert(1, (docs[0][0], hint_doc, None, docs[0][3]))
    seen, fallback = set(), None
    for cik, doc, ft, form in order[: max_docs + 1]:
        if doc in seen: continue
        seen.add(doc); txt = EP.fetch_doc(cik, acc, doc)
        if not txt: continue
        sec = section_of(txt, phrases)
        if sec and len(sec) >= 6000 and presented(sec): return sec, doc, form, txt
        if sec and (fallback is None or len(sec) > len(fallback[0])): fallback = (sec, doc, form, txt)
    return fallback if fallback else (None, None, None, None)
