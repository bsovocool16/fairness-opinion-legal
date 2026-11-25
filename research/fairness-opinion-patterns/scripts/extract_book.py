"""Best-effort WACC build-up fields from board-book text layers (SC 13E3 / SC TO exhibits). Board-book text is often scrambled, so
only label-adjacent numbers are kept."""
import re
P = r"(\d{1,2}(?:\.\d{1,2})?)\s*%"
def near(label, s, val=P, span=60):
    out = []
    for m in re.finditer(label, s, re.I):
        w = s[m.end(): m.end() + span]
        v = re.search(val, w)
        if v: out.append(float(v.group(1)))
    return out
def extract_book(t):
    t = t.replace("\xa0", " ")
    r = {}
    r["rf"] = near(r"risk[- ]free(?: rate)?(?: of return)?(?:\s*\([^)]{0,40}\))?\s*[:\-–]?", t)
    r["erp"] = near(r"(?:equity|market)(?: market)? risk premium(?:\s*\([^)]{0,40}\))?(?: - (?:low|high))?\s*[:\-–]?", t)
    r["size"] = near(r"(?:size|small[- ]cap(?:italization)?)(?: risk)? premium(?:\s*\([^)]{0,40}\))?\s*[:\-–]?", t)
    r["ubeta"] = near(r"(?:unlevered|asset)(?: asset)? beta(?:\s*\([^)]{0,40}\))?\s*[:\-–]?", t, r"(\d\.\d{2})", 40)
    r["lbeta"] = near(r"(?:relevered|levered|equity)(?: equity)? beta(?:\s*\([^)]{0,40}\))?\s*[:\-–]?", t, r"(\d\.\d{2})", 40)
    r["kd"] = near(r"(?:pre-tax )?cost of debt\s*[:\-–]?", t)
    r["wacc"] = [float(a) for a, b in re.findall(r"(\d{1,2}\.\d)\s*%\s*[-–]\s*(\d{1,2}\.\d)\s*%\s*(?:WACC|discount rate)", t, re.I)]
    m = re.search(r"(\d{1,2}|ten|twenty|thirty)[- ]year[^.]{0,40}?(?:treasury|CMT|government|bond|T-bond)", t, re.I)
    if m: g = m.group(1).lower(); r["rf_tenor"] = {"ten": 10, "twenty": 20, "thirty": 30}.get(g, int(g) if g.isdigit() else None)
    for k, p in {"bloomberg": r"bloomberg", "barra": r"barra|axioma|predicted beta", "adjusted": r"adjusted (?:equity )?beta|blume", "duffphelps": r"duff\s*&\s*phelps|kroll|ibbotson|sbbi|cost of capital navigator",
                 "supply_side": r"supply[- ]side", "historical_erp": r"historical (?:equity|market) risk premium|long-horizon", "weekly": r"weekly", "monthly": r"monthly", "two_year": r"2[- ]year (?:weekly|daily|beta)|two[- ]year", "five_year": r"5[- ]year|five[- ]year"}.items():
        r["f_" + k] = bool(re.search(p, t, re.I))
    return r
