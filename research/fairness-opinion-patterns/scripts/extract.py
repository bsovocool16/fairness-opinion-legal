"""Pull banker DCF inputs out of a proxy / 14D-9 / board-book text."""
import re
from banks import first_bank
N = r"(-?\d{1,2}(?:\.\d{1,3})?)"
TO = r"\s*%?\s*(?:to|through|and|-|–|—)\s*"
def norm(t):
    t = t.replace("’", "'").replace("\xa0", " ")
    t = re.sub(r"[ \t]*\n(?=[a-z(\$0-9%,;.])", " ", t)            # soft wraps
    t = re.sub(r"(?m)^([^\n]{140,}[a-z,;])[ \t]*\n(?=[A-Za-z])", r"\1 ", t)
    t = re.sub(r"\n\s*(?:\d{1,3}|TABLE OF CONTENTS|Table of Contents)\s*\n", "\n", t)
    t = re.sub(r"[ \t]+", " ", t)
    return t
HEAD = re.compile(r"(?im)^(?:[^\n]{0,60}?discounted cash flows?(?: analys[ie]s| valuation| approach| method)?\b[^\n]{0,80}$|[ \t]*(?:[\w'.,\- ]{0,40}\s)?discounted cash flows?(?: analys[ie]s| valuation)?[^\n\w]{0,4}(?:\.|:|—|–| -)[^\n]*|[^\n|•]{0,400}?\bperformed (?:a|an|its|separate|illustrative)(?: \w+){0,3} discounted cash flows? analys[ie]s[^\n]*)")
STOP = re.compile(r"(?im)^\s*(?:[\w'.&\- ]{0,40}\s)?(?:selected (?:public|publicly|comparable|precedent|companies|transactions|m&a)|precedent transaction|comparable compan|premiums? paid|leveraged buyout|lbo analysis|52-week|historical (?:stock|share|trading)|analyst (?:price )?targets|research analyst|sum[- ]of[- ]the[- ]parts|dividend discount|other (?:factors|matters|information)|miscellaneous|general\b|illustrative (?:present value of )?future|net asset value|liquidation analysis|opinion of)")
def _ok(s, m, skip_implied):
    return not (skip_implied and re.search(r"(?:impl(?:y|ied|ies)|median|average|mean)[^.;]{0,50}$", s[max(0, m.start() - 70): m.start() + 1], re.I))
def range_after(pat, s, unit="%", skip_implied=False, single=True):
    u = r"\s*%" if unit == "%" else r"\s*x"
    ms = [m for m in re.finditer(pat + r"[^.%$]{0,170}?" + N + (r"\s*%?" if unit == "%" else r"\s*x?") + TO + N + u, s, re.I) if _ok(s, m, skip_implied)]
    m = ms[0] if ms else None
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        return (min(a, b), max(a, b), m.start())
    if not single: return None
    ms = [m for m in re.finditer(pat + r"[^.%$]{0,60}?" + N + u, s, re.I) if _ok(s, m, skip_implied)]
    m = ms[0] if ms else None
    if m: v = float(m.group(1)); return (v, v, m.start())
    return None
def dcf_blocks(t):
    out = []; heads = [m for m in HEAD.finditer(t) if not re.search(r"\.{4,}|^\s*\|", m.group(0)) and not (len(m.group(0)) < 160 and re.search(r"\s\d{1,3}\s*$", m.group(0)))]
    for m in heads:
        s = t[m.start(): m.start() + 9000]
        st = STOP.search(s, len(m.group(0)) + 200)
        if st: s = s[:st.start()]
        if not re.search(r"discount rate|cost of capital|terminal|perpetuity", s, re.I): continue
        if out and m.start() < out[-1][0] + len(out[-1][1]): continue
        out.append((m.start(), s))
    return out
def offer_price(t):
    head = t[:250000]
    cands = re.findall(r"\$(\d{1,4}\.\d{2,4})(?: per (?:share|unit)(?: of [\w ]{0,40}?)?)?,? in cash", head)
    cands += re.findall(r"(?:right to receive|offer price of|merger consideration of|per share price of|purchase price of|cash consideration of)\s*\$(\d{1,4}\.\d{2,4})", head)
    if not cands: return None
    from collections import Counter
    return float(Counter(cands).most_common(1)[0][0])
FLAGS = {
 "capm": r"capital asset pricing model|\bCAPM\b", "wacc_mention": r"weighted average cost of capital|\bWACC\b", "coe_mention": r"cost of equity",
 "beta_bloomberg": r"bloomberg[^.]{0,60}beta|beta[^.]{0,80}bloomberg", "beta_barra": r"barra|predicted beta|axioma",
 "beta_adjusted": r"adjusted beta|blume|levered beta[^.]{0,30}adjusted", "beta_historical": r"historical beta|raw beta",
 "beta_peer": r"(?:selected|peer|comparable)[^.]{0,60}beta|beta[^.]{0,60}(?:selected|peer|comparable) compan",
 "size_premium": r"size premium|size risk premium|small[- ]company (?:risk )?premium", "company_specific": r"company[- ]specific (?:risk )?premium|specific risk premium|alpha",
 "duff_phelps_src": r"duff\s*&\s*phelps|kroll cost of capital|ibbotson|morningstar|sbbi|cost of capital navigator", "supply_side": r"supply[- ]side",
 "mid_year": r"mid-year convention|mid-period", "sbc_cash": r"stock-based compensation[^.]{0,80}(?:as a )?cash expense|treat(?:ed|ing) stock-based compensation as a cash",
 "nol": r"net operating loss|\bNOLs?\b", "perpetuity": r"perpetuity growth|terminal growth|long-term growth rate|perpetual growth|gordon growth",
 "exit_multiple": r"terminal (?:value |exit |forward |ebitda |)?multiple|exit multiple|terminal ebitda multiple|terminal value multiple",
 "levered_fcf": r"(?<!un)levered free cash flow|free cash flows to equity|dividend discount", "rounded": r"rounded to the nearest", "tv_decline": r"declin\w* (?:in perpetuity|of \d+(?:\.\d+)?%|at a rate)|perpetual decline|negative (?:terminal|perpetuity) growth",
 "professional_judgment": r"professional judgment", "illustrative": r"\billustrative\b", "synergies": r"synerg",
}
def extract_block(s):
    r = {}
    dr = range_after(r"discount rates?", s) or range_after(r"weighted average costs? of capital", s) or range_after(r"costs? of equity", s)
    if dr: r["dr_lo"], r["dr_hi"] = dr[0], dr[1]
    pg = range_after(r"(?:perpetuity|terminal|long[- ]term|perpetual)(?: free cash flow)? growth rates?", s, skip_implied=True) or range_after(r"growth rates? in perpetuity", s, skip_implied=True)
    if pg and -3 <= pg[0] <= 8: r["pg_lo"], r["pg_hi"] = pg[0], pg[1]
    EP1, EP2 = r"(?:terminal|exit)(?: value)?(?: [\w\-/]+){0,3} multiples?", r"multiples?(?: of [\w\-/ ]{0,40})?"
    em = range_after(EP1, s, "x", True, False) or range_after(EP2, s, "x", True, False) or range_after(EP1, s, "x", True) or range_after(EP2, s, "x", True)
    if em and 0.5 <= em[0] <= 60 and not ("pg_lo" in r and em[0] == em[1]): r["em_lo"], r["em_hi"] = em[0], em[1]
    erp = range_after(r"(?:equity|market) risk premi(?:um|a)", s)
    if erp and 2 <= erp[0] <= 12: r["erp_lo"], r["erp_hi"] = erp[0], erp[1]
    m = re.search(r"(?:unlevered|asset|relevered|levered)?\s*betas?[^.%$]{0,60}?(?:of|ranging from|range of)\s*(\d\.\d{1,2})(?:\s*(?:to|-|–)\s*(\d\.\d{1,2}))?", s, re.I)
    if m: r["beta_lo"] = float(m.group(1)); r["beta_hi"] = float(m.group(2) or m.group(1))
    sp = range_after(r"size premi(?:um|a)", s)
    if sp and 0 < sp[0] < 8: r["size_lo"], r["size_hi"] = sp[0], sp[1]
    m = re.search(r"(\d{1,2}|ten|twenty|thirty|five|seven)[- ]year\s+(?:U\.S\.\s+)?(?:treasury|government|risk[- ]free|t-bond|bond)", s, re.I)
    if m:
        w = {"ten": 10, "twenty": 20, "thirty": 30, "five": 5, "seven": 7}; g = m.group(1).lower(); r["rf_tenor"] = int(w.get(g, g if g.isdigit() else 0))
    rf = range_after(r"risk[- ]free(?: rate)?(?: of return)?", s)
    if rf and 0 < rf[0] < 9: r["rf_lo"], r["rf_hi"] = rf[0], rf[1]
    VR = r"\$\s?(\d{1,4}(?:\.\d{1,3})?)\s*(?:to|-|–|—|and|\|)\s*\$?\s?(\d{1,4}(?:\.\d{1,3})?)(?!\s*(?:billion|million|bn|mm|\d))"
    cands = []
    for m in re.finditer(r"(?:implied|reference|illustrative|indicated|resulting|range)[^$]{0,200}?" + VR, s, re.I | re.S): cands.append((0, m))
    for m in re.finditer(VR, s, re.I): cands.append((1, m))
    for m in re.finditer(r"\|\s*\$\s?(\d{1,4}\.\d{2})\s*\|\s*\$?\s?(\d{1,4}\.\d{2})\s*\|", s): cands.append((2, m))
    for pri, m in sorted(cands, key=lambda c: (c[0], c[1].start())):
        a, b = float(m.group(1)), float(m.group(2))
        ctx = s[m.end(): m.end() + 25].lower()
        if 0 < a < b < 12 * a + 2 and "billion" not in ctx and "million" not in ctx:
            r["v_lo"], r["v_hi"] = a, b; r["v_src"] = pri; break
    m = re.search(r"(?:as compared|compared|in comparison|relative)\s+(?:to|with)\s+(?:the\s+)?[^$]{0,120}?\$\s?(\d{1,4}(?:\.\d{1,3})?)", s, re.I | re.S)
    if m:
        cp = float(m.group(1))
        if cp in (r.get("v_lo"), r.get("v_hi")):
            m2 = re.search(r"\$\s?(\d{1,4}(?:\.\d{1,3})?)", s[m.end(): m.end() + 120].split("$", 1)[-1] if False else s[m.end(): m.end() + 160])
            mm = re.findall(r"\$\s?(\d{1,4}(?:\.\d{1,3})?)", s[m.end(): m.end() + 160])
            mm = [float(x) for x in mm if float(x) not in (r.get("v_lo"), r.get("v_hi"))]
            cp = mm[0] if mm else None
        if cp: r["cmp_price"] = cp
    ip = re.search(r"implied (?:perpetuity|terminal|perpetual)(?: free cash flow)? growth rates?[^.%$]{0,60}?" + N + r"\s*%?" + TO + N + r"\s*%", s, re.I)
    if ip: r["impl_pg_lo"], r["impl_pg_hi"] = sorted([float(ip.group(1)), float(ip.group(2))])
    ix = re.search(r"implied (?:terminal |exit )?(?:[\w\-/]+ ){0,3}multiples?[^.%$]{0,60}?" + N + r"\s*x?" + TO + N + r"\s*x", s, re.I)
    if ix: r["impl_em_lo"], r["impl_em_hi"] = sorted([float(ix.group(1)), float(ix.group(2))])
    for k, p in FLAGS.items(): r["f_" + k] = bool(re.search(p, s, re.I))
    m = re.search(r"(?:calendar|fiscal)?\s*years?\s*(?:ending\s*)?(?:\w+ \d{1,2}, )?(20\d\d|19\d\d)\s*(?:through|to|-|–)\s*(?:\w+ \d{1,2}, )?(20\d\d|19\d\d)", s, re.I)
    if m and 1 <= int(m.group(2)) - int(m.group(1)) + 1 <= 30: r["proj_years"] = int(m.group(2)) - int(m.group(1)) + 1
    return r
def extract_doc(t):
    t = norm(t); price = offer_price(t); rows = []
    # opinion section headings, to attribute banks when the block itself names none
    ops = [(m.start(), first_bank(m.group(0))) for m in re.finditer(r"(?im)^[^\n]{0,40}opinions? of [^\n]{3,120}$", t)]
    for i, (pos, s) in enumerate(dcf_blocks(t)):
        b = first_bank(s[:1500])
        if not b:
            prev = [bk for p, bk in ops if p < pos and bk]
            b = prev[-1] if prev else None
        if not b:
            mm = re.search(r"(?:^|[.:]\s|,\s)((?:[A-Z][\w&/.'\-]*\s?){1,5}?)\s(?:also |then |further )?(?:performed|calculated|conducted|estimated|derived|applied|used|discounted|utilized|determined|reviewed)\b", s[:600])
            if mm and not re.match(r"(?:The|This|In|Using|Based|Such|Its|We|Our|It|Each|A|An)\b", mm.group(1)): b = "other:" + re.sub(r"\s+", " ", re.sub(r"(?is)^.*?discounted cash flows?(?: analys[ie]s| approach| valuation)?\s*[.:\-–—]?\s*", "", mm.group(1))).strip()
        r = extract_block(s); r.update({"block_i": i, "bank": b, "pos": pos / max(1, len(t)), "headline_price": price, "block_len": len(s), "text": s[:6000]})
        rows.append(r)
    flags = {"is_13e3": bool(re.search(r"rule 13e-3|going private transaction|schedule 13e-3", t[:400000], re.I)),
             "cash_deal": bool(re.search(r"per share in cash|in cash, without interest", t[:200000], re.I)),
             "stock_deal": bool(re.search(r"exchange ratio", t[:200000], re.I)),
             "sponsor": bool(re.search(r"private equity|affiliates? of (?:\w+ ){0,3}(?:capital|partners)|sponsor", t[:150000], re.I)),
             "special_committee": bool(re.search(r"special committee|transaction committee|independent committee", t[:200000], re.I)),
             "tender": bool(re.search(r"tender offer", t[:60000], re.I)), "doc_len": len(t)}
    return rows, flags
