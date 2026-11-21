#!/usr/bin/env python3
"""Stage 2 of the ticker-to-proxy lifecycle: the banker's Excel valuation model, then the valuation it computes.

  python3 build_model.py <company.json> <deal_terms.json> <out dir>      writes model.xlsx and valuation.json

Tabs: Cover, Assumptions, Historicals, DCF, WACC, Comps, LBO, Sensitivity, Summary. Drafting conventions (references/lifecycle.md):
  - blue font: a hardcoded input; black: a formula on the same tab; green: a formula that pulls from another tab
  - every input lives on Assumptions, Historicals, Comps (peer data) or WACC (peer betas), with its source beside it
  - no number typed inside a formula other than structural constants (0, 1, 2, 4 quartile arguments, 0.5, 365)
  - one unit per model ($ in millions, shares in millions, per-share in $), stated on every tab
  - sensitivity grids are live formulas (no Excel data tables, which LibreOffice and some viewers do not compute)
After writing, the model is recalculated headless in LibreOffice and every output the deck and the letter need is read back
from the recalculated cells into valuation.json, with the cell it came from. No downstream number is computed in Python."""
import sys, math, shutil, subprocess, tempfile, statistics, datetime, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load, save, need, SCHEMAS, disclaimer, STATES
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.chart import BarChart, Reference
from openpyxl.workbook.properties import CalcProperties

BLUE, BLACK, GREEN, NAVY, GREY = "0000FF", "000000", "008000", "1F3864", "808080"
FMT = {"mm": '#,##0.0_);(#,##0.0);"–"_)', "pct": '0.0%_);(0.0%);"–"_)', "x": '0.0x_);(0.0x)', "ps": '$#,##0.00_);($#,##0.00)', "shares": '#,##0.0_);(#,##0.0)',
       "beta": '0.00_);(0.00)', "date": 'mmm d, yyyy', "year": '0"A"', "yearE": '0"E"', "int": '0', "factor": '0.000_);(0.000)', "flag": '0'}
THIN = Side(style="thin", color="000000")
UNITS = "($ in millions, except per-share data; shares in millions)"
SHEETS = ["Cover", "Assumptions", "Historicals", "DCF", "WACC", "Comps", "LBO", "Sensitivity", "Summary"]
N_PROJ = 5

class Tab:
    """One worksheet with the color convention applied by what is written: a number is an input (blue), a formula is black
    unless it reaches another tab (green). put() returns the absolute address for use in other formulas."""
    def __init__(self, wb, name, title, widths=None):
        self.ws = wb.create_sheet(name); self.name = name; ws = self.ws
        ws.sheet_view.showGridLines = False
        for col, w in (widths or {"A": 2, "B": 44}).items(): ws.column_dimensions[col].width = w
        ws["B1"] = title; ws["B1"].font = Font(bold=True, size=14, color=NAVY)
        ws["B2"] = UNITS; ws["B2"].font = Font(italic=True, size=9, color=GREY)
        ws.page_setup.orientation = "landscape"; ws.page_setup.fitToWidth = 1; ws.sheet_properties.pageSetUpPr.fitToPage = True
    def put(self, r, c, v, fmt=None, bold=False, note=None, italic=False, align=None):
        cell = self.ws.cell(row=r, column=c, value=v)
        if isinstance(v, str) and v.startswith("="): color = GREEN if "!" in v else BLACK
        elif isinstance(v, (int, float, datetime.date)) and not isinstance(v, bool): color = BLUE
        else: color = BLACK
        cell.font = Font(color=color, bold=bold, italic=italic, size=10)
        if fmt: cell.number_format = FMT.get(fmt, fmt)
        if align: cell.alignment = Alignment(horizontal=align)
        if note is not None:
            n = self.ws.cell(row=r, column=note[0], value=note[1]); n.font = Font(italic=True, size=9, color=GREY)
        return self.a(r, c)
    def label(self, r, text, c=2, bold=False, indent=0, italic=False):
        cell = self.ws.cell(row=r, column=c, value=text); cell.font = Font(bold=bold, italic=italic, size=10); cell.alignment = Alignment(indent=indent); return cell
    def header(self, r, c1, c2, text=None):
        for c in range(c1, c2 + 1):
            cell = self.ws.cell(row=r, column=c); cell.fill = PatternFill("solid", fgColor=NAVY); cell.font = Font(bold=True, color="FFFFFF", size=10)
        if text: self.ws.cell(row=r, column=c1, value=text)
    def colhead(self, r, c, text):
        cell = self.ws.cell(row=r, column=c, value=text); cell.font = Font(bold=True, size=10); cell.alignment = Alignment(horizontal="center", wrap_text=True)
        cell.border = Border(bottom=THIN); return cell
    def total(self, r, c1, c2):
        for c in range(c1, c2 + 1): self.ws.cell(row=r, column=c).border = Border(top=THIN)
    def a(self, r, c, absolute=True, sheet=True):
        ref = f"${L(c)}${r}" if absolute else f"{L(c)}{r}"
        return f"{self.name}!{ref}" if sheet else ref
    def loc(self, r, c): return f"{L(c)}{r}"

def r2(x, step): return round(round(x / step) * step, 6)
def clamp(x, lo, hi): return max(lo, min(hi, x))
def pctile(xs, q):
    xs = sorted(xs); k = (len(xs) - 1) * q; f = math.floor(k); c = min(f + 1, len(xs) - 1); return xs[f] + (xs[c] - xs[f]) * (k - f)

def defaults(co, terms):
    """Starting assumptions, all judgment inputs entered in blue and editable; each one's basis is written next to it."""
    t = co["target"]; A = [r for r in t["annual"] if r.get("revenue")]; last3 = A[-3:]
    def avg(f, base="revenue"):
        xs = [r[f] / r[base] for r in last3 if r.get(f) is not None and r.get(base)]; return sum(xs) / len(xs) if xs else None
    cagr = (A[-1]["revenue"] / A[-4]["revenue"]) ** (1 / 3) - 1 if len(A) >= 4 else ((A[-1]["revenue"] / A[0]["revenue"]) ** (1 / max(1, len(A) - 1)) - 1 if len(A) > 1 else 0.03)
    g_term = 0.025; g0 = clamp(cagr, -0.05, 0.15)
    growth = [r2(g0 + (g_term + 0.01 - g0) * i / (N_PROJ - 1), 0.0025) for i in range(N_PROJ)]
    # Year one starts from what has already happened: LTM revenue, plus the rest of the fiscal year at the year-two rate.
    # Without this a projection off the last 10-K can forecast a year below the twelve months already reported.
    LV = t["ltm"]["values"]; lfy_end = datetime.date.fromisoformat(A[-1]["period_end"])
    ltm_end = (t["ltm"]["sources"].get("revenue") or {}).get("ending")
    anchor = None
    if ltm_end and LV.get("revenue") and A[-1]["revenue"]:
        fy1_end = lfy_end + datetime.timedelta(days=365 + (1 if (lfy_end.month > 2 and (lfy_end.year + 1) % 4 == 0) else 0))
        rest = clamp((fy1_end - datetime.date.fromisoformat(ltm_end)).days / 365, 0, 1)
        g1 = LV["revenue"] * (1 + growth[1] * rest) / A[-1]["revenue"] - 1
        anchor = (g1, ltm_end, rest); growth[0] = r2(clamp(g1, -0.5, 1.0), 0.0025)
    ebitda_m = [((r.get("ebit") or 0) + (r.get("da") or 0)) / r["revenue"] for r in last3 if r.get("ebit") is not None]
    avg_m = sum(ebitda_m) / len(ebitda_m) if ebitda_m else 0.15
    ltm_m = ((LV.get("ebit") or 0) + (LV.get("da") or 0)) / LV["revenue"] if LV.get("revenue") and LV.get("ebit") is not None else None
    rising = ltm_m is not None and len(ebitda_m) >= 2 and ltm_m >= ebitda_m[-1] >= avg_m
    margin = r2(ltm_m if rising else avg_m, 0.0025)
    da = r2(avg("da") or 0.03, 0.0025); capex = r2(avg("capex") or da, 0.0025)
    nwc = r2((A[-1]["nwc"] / A[-1]["revenue"]) if A[-1].get("nwc") is not None else 0.10, 0.0025)
    peers = co["peers"]; mults, dcaps, betas = [], [], []
    for p in peers:
        v = p["ltm"]["values"]; eb = (v.get("ebit") or 0) + (v.get("da") or 0); mcap = p["price"]["last"] * p["shares_out_mm"]
        ev = mcap + p["balance"]["debt"] - p["balance"]["cash"] + (p["balance"].get("nci") or 0) + (p["balance"].get("preferred") or 0)
        if eb > 0 and 0 < ev / eb < 50: mults.append(ev / eb)
        dcaps.append(p["balance"]["debt"] / (p["balance"]["debt"] + mcap))
        if p["price"].get("beta_raw"): betas.append(p["price"]["beta_raw"])
    med = statistics.median(mults) if mults else 10.0
    lo, hi = (pctile(mults, 0.25), pctile(mults, 0.75)) if len(mults) >= 3 else (med * 0.85, med * 1.15)
    rf = co["market"]["risk_free"].get("rate") or 0.0425
    ltm = t["ltm"]["values"]; debt = t["balance"]["debt"] or 0
    kd = clamp((ltm.get("interest") or 0) / debt, rf + 0.005, 0.12) if debt > 0 and ltm.get("interest") else rf + 0.0175
    return {"growth": growth, "margin": [margin] * N_PROJ, "da": [da] * N_PROJ, "capex": [capex] * N_PROJ, "nwc": [nwc] * N_PROJ, "tax": [0.25] * N_PROJ,
            "rf": rf, "erp": 0.055, "size": 0.0, "kd": r2(kd, 0.0025), "tax_marginal": 0.25, "dcap": r2(statistics.median(dcaps), 0.05) if dcaps else 0.2,
            "wacc_step": 0.005, "g_mid": g_term, "g_step": 0.005, "exit_mid": r2(med, 0.5), "exit_step": 1.0, "midyear": 1,
            "comps_lo": r2(lo, 0.5), "comps_hi": max(r2(hi, 0.5), r2(lo, 0.5) + 0.5), "nm_cap": 50.0, "prem_lo": 0.25, "prem_hi": 0.45,
            "lbo_lev": 5.0, "lbo_rate": r2(rf + 0.04, 0.0025), "lbo_exit": r2(med, 0.5), "irr_lo": 0.20, "irr_hi": 0.25, "lbo_fees": 0.02, "hold": N_PROJ,
            "basis": {"growth": (f"year 1: LTM revenue to {anchor[1]} plus the remaining {anchor[2]:.2f} of the year at the year-2 rate; then " if anchor else "")
                                + f"3-year revenue CAGR {cagr:.1%} (capped -5% to 15%), fading to terminal growth + 1.0% by year {N_PROJ}",
                      "margin": (f"LTM EBITDA margin {ltm_m:.1%}, held flat: margins have risen (3-year average {avg_m:.1%})" if rising else f"3-year average EBITDA margin {avg_m:.1%} (EBIT + D&A over revenue)"), "da": "3-year average D&A / revenue", "capex": "3-year average capex / revenue",
                      "nwc": "latest fiscal year NWC (current assets less cash, less current liabilities excluding debt) / revenue",
                      "tax": "U.S. federal 21% plus a blended state rate", "exit": "peer median EV / LTM EBITDA, rounded to 0.5x", "comps": "peer 25th-75th percentile EV / LTM EBITDA, rounded to 0.5x",
                      "erp": "long-horizon equity risk premium, judgment input", "kd": "LTM interest expense / total debt (bounded rf + 0.5% to 12%)", "dcap": "peer median debt / total capitalization, rounded to 5%",
                      "prem": "illustrative control-premium range, judgment input; replace with a premiums-paid study for the sector", "lbo": "judgment inputs typical of a sponsor financing"}}

def build(co, terms, out):
    t = co["target"]; D = defaults(co, terms); peers = co["peers"]; reg = {}
    A = [r for r in t["annual"] if r.get("revenue")][-5:]; nA = len(A)
    wb = Workbook(); wb.remove(wb.active)
    tabs = {}
    # ---------------- Cover ----------------
    cv = Tab(wb, "Cover", f"{t['name']} — Illustrative Valuation Model", {"A": 2, "B": 30, "C": 70}); tabs["Cover"] = cv
    rows = [("Company", f"{t['name']} ({t.get('exchange') or ''}: {t['ticker']})"), ("Transaction (hypothetical)", f"Acquisition by {terms['buyer']} for ${terms['offer_price']:,.2f} per share in {terms['consideration']}"),
            ("Financial advisor (hypothetical)", terms["advisor"]), ("Valuation date", terms["opinion_date"]), ("Data as of", co["as_of"]),
            ("Sources", "SEC EDGAR XBRL company facts and submissions; daily share prices (Yahoo Finance / Stooq); FRED DGS10 10-year Treasury"),
            ("Projections", "Illustrative, derived from reported history on the Assumptions tab; not management projections")]
    for i, (k, v) in enumerate(rows, 4): cv.label(i, k, bold=True); cv.ws.cell(row=i, column=3, value=v)
    r = 13; cv.label(r, "Color code", bold=True)
    for i, (txt, col) in enumerate([("1,000.0   hardcoded input or historical figure", BLUE), ("1,000.0   formula on the same tab", BLACK), ("1,000.0   formula linking another tab", GREEN)], r + 1):
        c = cv.ws.cell(row=i, column=3, value=txt); c.font = Font(color=col)
    r = 18; cv.label(r, "Tabs", bold=True)
    desc = {"Assumptions": "every judgment input, with its basis", "Historicals": "reported financials from XBRL, with the tag and filing", "DCF": "unlevered free cash flow, both terminal value methods, equity bridge",
            "WACC": "CAPM cost of equity with peer betas unlevered and relevered", "Comps": "selected public companies, multiples and implied value", "LBO": "sponsor ability-to-pay at target returns",
            "Sensitivity": "per-share value across WACC and terminal assumptions", "Summary": "transaction overview and the summary of analyses (football field)"}
    for i, (k, v) in enumerate(desc.items(), r + 1): cv.ws.cell(row=i, column=2, value=k).font = Font(bold=True, size=10); cv.ws.cell(row=i, column=3, value=v)
    c = cv.ws.cell(row=29, column=2, value=disclaimer(terms["advisor"], t["name"])); c.font = Font(italic=True, color="C00000", size=9)
    cv.ws.merge_cells("B29:C31"); c.alignment = Alignment(wrap_text=True, vertical="top")

    # ---------------- Assumptions ----------------
    asm = Tab(wb, "Assumptions", "Assumptions", {"A": 2, "B": 44, "C": 13, "D": 13, "E": 13, "F": 13, "G": 13, "H": 14, "I": 70}); tabs["Assumptions"] = asm
    r = 4; asm.header(r, 2, 9, "Transaction and market data"); r += 1
    P = t["price"]; B = t["balance"]
    def scalar(label, v, fmt, key, source=""):
        nonlocal r
        asm.label(r, label, indent=1); reg[key] = asm.put(r, 3, v, fmt, note=(9, source)); r += 1; return reg[key]
    vd = datetime.date.fromisoformat(terms["opinion_date"])
    scalar("Valuation date", vd, "date", "val_date", "the opinion date; cash flows before it are excluded (stub period)")
    scalar("Unaffected share price", float(terms["unaffected_price"]), "ps", "px_unaff", f"closing price on {terms['unaffected_date']} ({P['source']})")
    scalar("Offer price per share", float(terms["offer_price"]), "ps", "px_offer", "the hypothetical deal terms (deal_terms.json)")
    scalar("52-week high", P["high_52w"], "ps", "px_hi", f"daily closes, 52 weeks to {P['date']}")
    scalar("52-week low", P["low_52w"], "ps", "px_lo", f"daily closes, 52 weeks to {P['date']}")
    scalar("30-trading-day average", P["avg_30d"], "ps", "px_30d", "simple average of daily closes")
    scalar("Shares outstanding (mm)", t["shares_out_mm"], "shares", "shares", f"{t['shares_source'].get('tag', '')} as of {t['shares_source'].get('as_of', '')}; {t['shares_source'].get('basis', '')}; replace with fully diluted (treasury method) from the latest 10-Q")
    src = lambda k: (lambda s: f"{s.get('tag', '')} {s.get('form', '')} {s.get('period', '')}".strip())(B.get("sources", {}).get(k, {}))
    scalar("Total debt", B["debt"], "mm", "debt", f"balance sheet as of {B['as_of']}: {B.get('debt_basis', '')}; {src('debt_total') or src('debt_noncurrent')}")
    scalar("Cash and short-term investments", B["cash"], "mm", "cash", f"balance sheet as of {B['as_of']}: {src('cash')}")
    scalar("Noncontrolling interests", B.get("nci") or 0, "mm", "nci", f"balance sheet as of {B['as_of']}")
    scalar("Preferred stock", B.get("preferred") or 0, "mm", "pref", f"balance sheet as of {B['as_of']}")
    r += 1; asm.header(r, 2, 9, "Projection drivers (illustrative; not management projections)"); r += 1
    fy0 = A[-1]["fy"]
    asm.label(r, "Fiscal year", bold=True)
    # year headers are formulas off the last historical year so the model rolls forward by changing one input
    reg["proj_year_row"] = r
    for i in range(N_PROJ):
        asm.put(r, 3 + i, f"=Historicals!{L(2 + nA)}$4+{1}" if i == 0 else f"={L(2 + i)}{r}+1", "yearE", bold=True, align="center")
    asm.colhead(r, 8, "3-yr hist."); asm.colhead(r, 9, "Basis"); r += 1
    drivers = [("Revenue growth", "growth", "rev_g"), ("EBITDA margin", "margin", "ebitda_m"), ("D&A % of revenue", "da", "da_pct"), ("Capex % of revenue", "capex", "capex_pct"),
               ("Net working capital % of revenue", "nwc", "nwc_pct"), ("Cash tax rate on EBIT", "tax", "tax_pct")]
    for label, k, hk in drivers:
        asm.label(r, label, indent=1)
        for i in range(N_PROJ): asm.put(r, 3 + i, D[k][i], "pct")
        reg[f"drv_{k}"] = r
        asm.put(r, 8, None, "pct")   # the 3-year reference average is written once the Historicals rows are known
        asm.ws.cell(row=r, column=9, value=D["basis"].get(k, "")).font = Font(italic=True, size=9, color=GREY); r += 1
    r += 1; asm.header(r, 2, 9, "Discount rate"); r += 1
    scalar("Risk-free rate", D["rf"], "pct", "rf", co["market"]["risk_free"].get("source", "") + (f", {co['market']['risk_free'].get('date')}" if co["market"]["risk_free"].get("date") else ""))
    scalar("Equity risk premium", D["erp"], "pct", "erp", D["basis"]["erp"])
    scalar("Size premium", D["size"], "pct", "size", "judgment input; 0% unless the target is small relative to peers")
    scalar("Pre-tax cost of debt", D["kd"], "pct", "kd", D["basis"]["kd"])
    scalar("Marginal tax rate", D["tax_marginal"], "pct", "tax_m", "for unlevering and relevering beta and the debt tax shield")
    scalar("Target debt / total capitalization", D["dcap"], "pct", "dcap", D["basis"]["dcap"] + "; peer median shown on the WACC tab")
    scalar("WACC sensitivity step", D["wacc_step"], "pct", "wacc_step", "rows of the sensitivity grids; the selected range is midpoint ± one step")
    r += 1; asm.header(r, 2, 9, "Terminal value"); r += 1
    scalar("Perpetuity growth rate (midpoint)", D["g_mid"], "pct", "g_mid", "long-run nominal growth, judgment input")
    scalar("Perpetuity growth step", D["g_step"], "pct", "g_step", "selected range is midpoint ± one step")
    scalar("Exit multiple, EV / EBITDA (midpoint)", D["exit_mid"], "x", "exit_mid", D["basis"]["exit"] + "; the target's own multiple at the unaffected price is beside it, for reference")
    exit_ref_row = r - 1
    scalar("Exit multiple step", D["exit_step"], "x", "exit_step", "selected range is midpoint ± one step")
    scalar("Mid-year convention (1 = on, 0 = off)", D["midyear"], "flag", "midyear", "cash flows assumed to arrive mid-period")
    r += 1; asm.header(r, 2, 9, "Selected public companies"); r += 1
    scalar("Selected EV / LTM EBITDA, low", D["comps_lo"], "x", "comps_lo", D["basis"]["comps"])
    scalar("Selected EV / LTM EBITDA, high", D["comps_hi"], "x", "comps_hi", D["basis"]["comps"])
    scalar("Multiples above this are shown as NM", D["nm_cap"], "x", "nm_cap", "excluded from the statistics, as is any negative EBITDA")
    r += 1; asm.header(r, 2, 9, "Premiums paid"); r += 1
    scalar("Premium to unaffected price, low", D["prem_lo"], "pct", "prem_lo", D["basis"]["prem"])
    scalar("Premium to unaffected price, high", D["prem_hi"], "pct", "prem_hi", D["basis"]["prem"])
    r += 1; asm.header(r, 2, 9, "Leveraged buyout"); r += 1
    scalar("Total leverage, x LTM EBITDA", D["lbo_lev"], "x", "lbo_lev", D["basis"]["lbo"])
    scalar("Blended interest rate", D["lbo_rate"], "pct", "lbo_rate", "risk-free rate plus about 400 bp, judgment input")
    scalar("Exit multiple, EV / EBITDA", D["lbo_exit"], "x", "lbo_exit", "peer median EV / LTM EBITDA, rounded to 0.5x")
    scalar("Target IRR, low", D["irr_lo"], "pct", "irr_lo", "sponsor return threshold, judgment input")
    scalar("Target IRR, high", D["irr_hi"], "pct", "irr_hi", "sponsor return threshold, judgment input")
    scalar("Transaction fees and expenses, % of EV", D["lbo_fees"], "pct", "lbo_fees", "judgment input")
    scalar("Holding period (years)", D["hold"], "int", "hold", f"equal to the {N_PROJ}-year projection period")
    asm.ws.freeze_panes = "C4"

    # ---------------- Historicals ----------------
    hs = Tab(wb, "Historicals", "Historical Financials (as reported, from SEC XBRL)", {"A": 2, "B": 40, **{L(3 + i): 12 for i in range(nA + 1)}, L(4 + nA): 80}); tabs["Historicals"] = hs
    hs.header(3, 2, 3 + nA + 1, "Fiscal year ended"); C_LTM = 3 + nA
    for i, row in enumerate(A): hs.put(4, 3 + i, row["fy"], "year", bold=True, align="center"); hs.put(5, 3 + i, datetime.date.fromisoformat(row["period_end"]), "date", align="center")
    hs.colhead(4, C_LTM, "LTM"); ltm_src = t["ltm"]["sources"].get("revenue", {})
    hs.ws.cell(row=5, column=C_LTM, value=ltm_src.get("ending") or "").alignment = Alignment(horizontal="center"); hs.ws.cell(row=5, column=C_LTM).font = Font(size=9, color=BLUE)
    hs.colhead(4, C_LTM + 1, "Source (XBRL tag, form, filed)"); LV = t["ltm"]["values"]
    hrows = {}; r = 6
    def raw(label, key, ltm_key=None, fmt="mm"):
        nonlocal r
        hs.label(r, label, indent=1)
        for i, row in enumerate(A):
            v = row.get(key)
            if v is not None: hs.put(r, 3 + i, round(v, 3), fmt)
        lk = ltm_key if ltm_key is not None else key
        if lk and LV.get(lk) is not None: hs.put(r, C_LTM, round(LV[lk], 3), fmt)
        s = A[-1].get("sources", {}).get(key) or {}
        hs.ws.cell(row=r, column=C_LTM + 1, value=f"{s.get('tag', '')} · {s.get('form', '')} filed {s.get('filed', '')}" if s else "").font = Font(size=8, color=GREY)
        hrows[key] = r; r += 1
    def calc(label, key, f, fmt="pct", cols=None, italic=True, bold=False):
        nonlocal r
        hs.label(r, label, indent=2 if italic else 1, italic=italic, bold=bold)
        for c in (cols or range(3, C_LTM + 1)):
            hs.put(r, c, f(c), fmt, italic=italic, bold=bold)
        hrows[key] = r; r += 1
    raw("Revenue", "revenue")
    calc("% growth", "rev_g", lambda c: f"=IFERROR({L(c)}{hrows['revenue']}/{L(c - 1)}{hrows['revenue']}-1,\"\")", cols=range(4, 3 + nA))
    raw("Operating income (EBIT)", "ebit"); raw("Depreciation and amortization", "da")
    calc("EBITDA", "ebitda", lambda c: f"={L(c)}{hrows['ebit']}+{L(c)}{hrows['da']}", fmt="mm", italic=False, bold=True); hs.total(hrows["ebitda"], 3, C_LTM)
    calc("% margin", "ebitda_m", lambda c: f"=IFERROR({L(c)}{hrows['ebitda']}/{L(c)}{hrows['revenue']},\"\")")
    calc("D&A % of revenue", "da_pct", lambda c: f"=IFERROR({L(c)}{hrows['da']}/{L(c)}{hrows['revenue']},\"\")")
    raw("Capital expenditures", "capex")
    calc("% of revenue", "capex_pct", lambda c: f"=IFERROR({L(c)}{hrows['capex']}/{L(c)}{hrows['revenue']},\"\")")
    raw("Net working capital (ex. cash and debt)", "nwc", ltm_key="")
    calc("% of revenue", "nwc_pct", lambda c: f"=IFERROR({L(c)}{hrows['nwc']}/{L(c)}{hrows['revenue']},\"\")", cols=range(3, 3 + nA))
    raw("Interest expense", "interest"); raw("Pre-tax income", "pretax"); raw("Income tax expense", "tax")
    calc("Effective tax rate", "eff_tax", lambda c: f"=IFERROR({L(c)}{hrows['tax']}/{L(c)}{hrows['pretax']},\"\")")
    raw("Net income", "net_income"); raw("Stock-based compensation", "sbc")
    hs.ws.cell(row=r + 1, column=2, value="LTM = latest fiscal year + current year-to-date - prior year-to-date, from the 10-Q; NWC is a fiscal-year-end balance.").font = Font(italic=True, size=9, color=GREY)
    hs.ws.freeze_panes = "C6"
    reg.update({"h_rev_ltm": hs.a(hrows["revenue"], C_LTM), "h_ebitda_ltm": hs.a(hrows["ebitda"], C_LTM), "h_ebit_ltm": hs.a(hrows["ebit"], C_LTM)})
    # patch the Assumptions 3-yr reference averages now the Historicals rows are known
    for label, k, hk in drivers:
        rr = reg[f"drv_{k}"]; key = {"growth": "rev_g", "margin": "ebitda_m", "da": "da_pct", "capex": "capex_pct", "nwc": "nwc_pct", "tax": "eff_tax"}[k]
        last = 2 + nA; first = max(3 if key != "rev_g" else 4, last - 2)
        asm.ws.cell(row=rr, column=8).value = f"=IFERROR(AVERAGE(Historicals!{L(first)}{hrows[key]}:{L(last)}{hrows[key]}),\"\")"; asm.ws.cell(row=rr, column=8).font = Font(color=GREEN, size=10)

    # ---------------- WACC ----------------
    wc = Tab(wb, "WACC", "Weighted Average Cost of Capital", {"A": 2, "B": 40, "C": 10, "D": 12, "E": 12, "F": 12, "G": 12, "H": 12, "I": 12, "J": 40}); tabs["WACC"] = wc
    # filled after Comps so it can link market cap and debt
    # ---------------- Comps ----------------
    cp = Tab(wb, "Comps", "Selected Public Companies Analysis", {"A": 2, "B": 36, "C": 9, **{L(c): 11 for c in range(4, 19)}}); tabs["Comps"] = cp
    heads = ["Company", "Ticker", "Share price", "Shares (mm)", "Equity value", "Debt", "Cash", "NCI + pref.", "Enterprise value", "LTM revenue", "LTM EBIT", "LTM D&A", "LTM EBITDA",
             "EV / LTM revenue", "EV / LTM EBITDA", "EV / LTM EBIT", "EBITDA margin"]
    cp.header(4, 2, 18)
    for i, h in enumerate(heads): c = cp.ws.cell(row=4, column=2 + i, value=h); c.alignment = Alignment(horizontal="center" if i else "left", wrap_text=True)
    cp.ws.row_dimensions[4].height = 30
    r0 = 5
    for j, p in enumerate(peers):
        r = r0 + j; v = p["ltm"]["values"]; b = p["balance"]
        cp.ws.cell(row=r, column=2, value=p["name"]); cp.ws.cell(row=r, column=3, value=p["ticker"]).alignment = Alignment(horizontal="center")
        cp.put(r, 4, p["price"]["last"], "ps"); cp.put(r, 5, p["shares_out_mm"], "shares"); cp.put(r, 6, f"=D{r}*E{r}", "mm")
        cp.put(r, 7, round(b["debt"], 3), "mm"); cp.put(r, 8, round(b["cash"], 3), "mm"); cp.put(r, 9, round((b.get("nci") or 0) + (b.get("preferred") or 0), 3), "mm")
        cp.put(r, 10, f"=F{r}+G{r}-H{r}+I{r}", "mm"); cp.put(r, 11, round(v.get("revenue") or 0, 3), "mm"); cp.put(r, 12, round(v.get("ebit") or 0, 3), "mm"); cp.put(r, 13, round(v.get("da") or 0, 3), "mm")
        cp.put(r, 14, f"=L{r}+M{r}", "mm")
        for c, den in ((15, "K"), (16, "N"), (17, "L")): cp.put(r, c, f"=IF(OR({den}{r}<=0,J{r}/{den}{r}>Assumptions!{reg['nm_cap'].split('!')[1]}),\"NM\",J{r}/{den}{r})", "x", align="right")
        cp.put(r, 18, f"=IFERROR(N{r}/K{r},\"\")", "pct")
    rN = r0 + len(peers) - 1; r = rN + 1; cp.total(r, 2, 18)
    stats = [("Maximum", "MAX({})"), ("75th percentile", "QUARTILE({},3)"), ("Median", "MEDIAN({})"), ("Mean", "AVERAGE({})"), ("25th percentile", "QUARTILE({},1)"), ("Minimum", "MIN({})")]
    srow = {}
    for name, f in stats:
        cp.label(r, name, bold=True)
        for c in (15, 16, 17, 18): cp.put(r, c, "=" + f.format(f"{L(c)}{r0}:{L(c)}{rN}"), "x" if c < 18 else "pct", bold=True)
        srow[name] = r; r += 1
    r += 1; cp.label(r, f"{t['name']} at the unaffected price (for reference; not in the statistics)", italic=True); rt = r
    cp.ws.cell(row=r, column=3, value=t["ticker"]).alignment = Alignment(horizontal="center")
    cp.put(r, 4, f"={reg['px_unaff']}", "ps"); cp.put(r, 5, f"={reg['shares']}", "shares"); cp.put(r, 6, f"=D{r}*E{r}", "mm"); cp.put(r, 7, f"={reg['debt']}", "mm"); cp.put(r, 8, f"={reg['cash']}", "mm")
    cp.put(r, 9, f"={reg['nci']}+{reg['pref']}", "mm"); cp.put(r, 10, f"=F{r}+G{r}-H{r}+I{r}", "mm"); cp.put(r, 11, f"={reg['h_rev_ltm']}", "mm"); cp.put(r, 12, f"={reg['h_ebit_ltm']}", "mm")
    cp.put(r, 13, f"=Historicals!{L(C_LTM)}{hrows['da']}", "mm"); cp.put(r, 14, f"=L{r}+M{r}", "mm")
    for c, den in ((15, "K"), (16, "N"), (17, "L")): cp.put(r, c, f"=IFERROR(J{r}/{den}{r},\"NM\")", "x")
    cp.put(r, 18, f"=IFERROR(N{r}/K{r},\"\")", "pct")
    r += 3; cp.header(r, 2, 6, "Implied value per share"); r += 1
    cp.colhead(r, 4, "Low"); cp.colhead(r, 5, "High"); r += 1
    cp.label(r, "Selected EV / LTM EBITDA multiple", indent=1); cp.put(r, 4, f"={reg['comps_lo']}", "x"); cp.put(r, 5, f"={reg['comps_hi']}", "x"); rm = r; r += 1
    cp.label(r, "Target LTM EBITDA", indent=1); cp.put(r, 4, f"={reg['h_ebitda_ltm']}", "mm"); cp.put(r, 5, f"={reg['h_ebitda_ltm']}", "mm"); re_ = r; r += 1
    cp.label(r, "Implied enterprise value", indent=1); cp.put(r, 4, f"=D{rm}*D{re_}", "mm"); cp.put(r, 5, f"=E{rm}*E{re_}", "mm"); rev_ = r; r += 1
    # net adjustments are defined on the DCF tab; filled once that address exists
    cp.label(r, "Less: net debt, NCI and preferred", indent=1); radj = r; r += 1
    cp.label(r, "Implied equity value", indent=1); cp.put(r, 4, f"=D{rev_}+D{radj}", "mm"); cp.put(r, 5, f"=E{rev_}+E{radj}", "mm"); req = r; cp.total(r, 4, 5); r += 1
    cp.label(r, "Implied value per share", bold=True); reg["comps_ps_lo"] = cp.put(r, 4, f"=D{req}/{reg['shares']}", "ps", bold=True); reg["comps_ps_hi"] = cp.put(r, 5, f"=E{req}/{reg['shares']}", "ps", bold=True)
    reg.update({"comps_median_ebitda": cp.a(srow["Median"], 16), "comps_q1_ebitda": cp.a(srow["25th percentile"], 16), "comps_q3_ebitda": cp.a(srow["75th percentile"], 16),
                "comps_median_rev": cp.a(srow["Median"], 15), "tgt_ev_ltm_ebitda_unaff": cp.a(rt, 16)})
    cp.ws.cell(row=r + 2, column=2, value=f"Peers: {co['peer_basis']}. Balance sheets as of each company's latest 10-Q or 10-K; prices as of {co['as_of']}.").font = Font(italic=True, size=9, color=GREY)
    cp.ws.freeze_panes = "C5"
    cell = asm.ws.cell(row=exit_ref_row, column=4, value=f"=Comps!$P${rt}"); cell.font = Font(color=GREEN, size=10, italic=True); cell.number_format = FMT["x"]
    cell = asm.ws.cell(row=exit_ref_row, column=5, value=f"=Comps!$P${srow['Median']}"); cell.font = Font(color=GREEN, size=10, italic=True); cell.number_format = FMT["x"]
    asm.ws.cell(row=exit_ref_row - 1, column=4, value="target").font = Font(italic=True, size=8, color=GREY); asm.ws.cell(row=exit_ref_row - 1, column=5, value="peer median").font = Font(italic=True, size=8, color=GREY)
    reg["comps_table"] = f"Comps!B{r0}:R{rN}"; reg["comps_stats"] = f"Comps!B{srow['Maximum']}:R{srow['Minimum']}"; reg["comps_target_row"] = f"Comps!B{rt}:R{rt}"

    # ---------------- WACC (now that Comps exists) ----------------
    wc.header(4, 2, 10, "Peer betas"); heads = ["Company", "Ticker", "Raw beta", "Equity value", "Debt", "Debt / equity", "Debt / total cap.", "Unlevered beta", "Beta basis"]
    for i, h in enumerate(heads): c = wc.ws.cell(row=4, column=2 + i, value=h); c.alignment = Alignment(horizontal="center" if i else "left", wrap_text=True)
    wc.ws.row_dimensions[4].height = 30
    for j, p in enumerate(peers):
        r = 5 + j; cr = r0 + j
        wc.put(r, 2, f"=Comps!B{cr}"); wc.put(r, 3, f"=Comps!C{cr}", align="center")
        wc.put(r, 4, p["price"].get("beta_raw"), "beta") if p["price"].get("beta_raw") is not None else None
        wc.put(r, 5, f"=Comps!F{cr}", "mm"); wc.put(r, 6, f"=Comps!G{cr}", "mm"); wc.put(r, 7, f"=IFERROR(F{r}/E{r},\"\")", "pct"); wc.put(r, 8, f"=IFERROR(F{r}/(E{r}+F{r}),\"\")", "pct")
        wc.put(r, 9, f"=IFERROR(D{r}/(1+(1-{reg['tax_m']})*G{r}),\"\")", "beta"); wc.ws.cell(row=r, column=10, value=p["price"].get("beta_basis", "")).font = Font(size=8, color=GREY)
    wN = 5 + len(peers) - 1; r = wN + 1; wc.total(r, 2, 9)
    wc.label(r, "Median", bold=True); wc.put(r, 4, f"=MEDIAN(D5:D{wN})", "beta", bold=True); wc.put(r, 8, f"=MEDIAN(H5:H{wN})", "pct", bold=True); wc.put(r, 9, f"=MEDIAN(I5:I{wN})", "beta", bold=True); wmed = r; r += 1
    wc.label(r, "Mean", bold=True); wc.put(r, 4, f"=AVERAGE(D5:D{wN})", "beta"); wc.put(r, 8, f"=AVERAGE(H5:H{wN})", "pct"); wc.put(r, 9, f"=AVERAGE(I5:I{wN})", "beta"); r += 1
    wc.label(r, f"{t['name']} (reference)", italic=True); wc.put(r, 3, t["ticker"], align="center")
    if t["price"].get("beta_raw") is not None: wc.put(r, 4, t["price"]["beta_raw"], "beta")
    wc.ws.cell(row=r, column=10, value=t["price"].get("beta_basis", "")).font = Font(size=8, color=GREY); r += 2
    wc.header(r, 2, 4, "Cost of capital"); r += 1
    def wl(label, f, fmt, key=None, bold=False, note=""):
        nonlocal r
        wc.label(r, label, indent=0 if bold else 1, bold=bold); addr = wc.put(r, 4, f, fmt, bold=bold)
        if note: wc.ws.cell(row=r, column=5, value=note).font = Font(italic=True, size=9, color=GREY)
        if key: reg[key] = addr
        r += 1; return wc.loc(r - 1, 4)
    a_bu = wl("Unlevered beta (peer median)", f"=I{wmed}", "beta", "beta_u")
    a_dc = wl("Target debt / total capitalization", f"={reg['dcap']}", "pct", None, note="Assumptions tab; peer median shown above")
    a_de = wl("Implied debt / equity", f"={a_dc}/(1-{a_dc})", "pct")
    a_bl = wl("Relevered beta", f"={a_bu}*(1+(1-{reg['tax_m']})*{a_de})", "beta", "beta_l", note="Hamada: βL = βU × (1 + (1 - t) × D/E)")
    a_rf = wl("Risk-free rate", f"={reg['rf']}", "pct"); a_erp = wl("Equity risk premium", f"={reg['erp']}", "pct"); a_sz = wl("Size premium", f"={reg['size']}", "pct")
    a_ke = wl("Cost of equity", f"={a_rf}+{a_bl}*{a_erp}+{a_sz}", "pct", "ke", bold=True, note="CAPM: rf + β × ERP + size premium")
    a_kd = wl("Pre-tax cost of debt", f"={reg['kd']}", "pct"); a_kdat = wl("After-tax cost of debt", f"={a_kd}*(1-{reg['tax_m']})", "pct", "kd_at")
    wc.total(r, 4, 4)
    wl("WACC", f"=(1-{a_dc})*{a_ke}+{a_dc}*{a_kdat}", "pct", "wacc", bold=True)
    wc.ws.freeze_panes = "C5"

    # ---------------- DCF ----------------
    dc = Tab(wb, "DCF", "Discounted Cash Flow Analysis", {"A": 2, "B": 40, **{L(c): 12 for c in range(3, 9)}, "I": 4, "J": 40}); tabs["DCF"] = dc
    C0 = 3; cols = list(range(C0 + 1, C0 + 1 + N_PROJ)); last = cols[-1]
    dc.header(3, 2, last, "Fiscal year"); dc.put(4, C0, f"=Historicals!{L(2 + nA)}4", "year", bold=True, align="center")
    for i, c in enumerate(cols): dc.put(4, c, f"=Assumptions!{L(3 + i)}{reg['proj_year_row']}", "yearE", bold=True, align="center")
    dc.label(5, "Period ending", italic=True); dc.put(5, C0, f"=Historicals!{L(2 + nA)}5", "date", align="center")
    for c in cols: dc.put(5, c, f"=EDATE({L(c - 1)}5,12)", "date", align="center")
    R = {}; r = 6
    def line(key, label, f0, f, fmt="mm", bold=False, italic=False, indent=1):
        nonlocal r
        dc.label(r, label, bold=bold, italic=italic, indent=indent)
        if f0 is not None: dc.put(r, C0, f0, fmt, bold=bold, italic=italic)
        for i, c in enumerate(cols): dc.put(r, c, f(i, c), fmt, bold=bold, italic=italic)
        R[key] = r; r += 1
    hcol = L(2 + nA); dr = lambda k, i: f"Assumptions!{L(3 + i)}{reg['drv_' + k]}"
    line("rev", "Revenue", f"=Historicals!{hcol}{hrows['revenue']}", lambda i, c: f"={L(c - 1)}{R['rev'] if 'rev' in R else r}*(1+{L(c)}{r + 1})", bold=True, indent=0)
    line("g", "% growth", None, lambda i, c: f"={dr('growth', i)}", "pct", italic=True, indent=2)
    line("ebitda", "EBITDA", f"=Historicals!{hcol}{hrows['ebitda']}", lambda i, c: f"={L(c)}{R['rev']}*{L(c)}{r + 1}", bold=True, indent=0)
    line("m", "% margin", None, lambda i, c: f"={dr('margin', i)}", "pct", italic=True, indent=2)
    line("da", "Less: depreciation and amortization", f"=-Historicals!{hcol}{hrows['da']}", lambda i, c: f"=-{L(c)}{R['rev']}*{dr('da', i)}")
    line("ebit", "EBIT", f"={L(C0)}{R['ebitda']}+{L(C0)}{R['da']}", lambda i, c: f"={L(c)}{R['ebitda']}+{L(c)}{R['da']}", bold=True, indent=0); dc.total(R["ebit"], C0, last)
    line("tax", "Less: taxes on EBIT", None, lambda i, c: f"=-{L(c)}{R['ebit']}*{dr('tax', i)}")
    line("nopat", "NOPAT", None, lambda i, c: f"={L(c)}{R['ebit']}+{L(c)}{R['tax']}", bold=True, indent=0); dc.total(R["nopat"], C0 + 1, last)
    line("addda", "Plus: depreciation and amortization", None, lambda i, c: f"=-{L(c)}{R['da']}")
    line("capex", "Less: capital expenditures", f"=-Historicals!{hcol}{hrows['capex']}", lambda i, c: f"=-{L(c)}{R['rev']}*{dr('capex', i)}")
    line("nwc", "Net working capital (memo)", f"=Historicals!{hcol}{hrows['nwc']}", lambda i, c: f"={L(c)}{R['rev']}*{dr('nwc', i)}", italic=True, indent=2)
    line("dnwc", "Less: increase in net working capital", None, lambda i, c: f"=-({L(c)}{R['nwc']}-{L(c - 1)}{R['nwc']})")
    line("ufcf", "Unlevered free cash flow", None, lambda i, c: f"={L(c)}{R['nopat']}+{L(c)}{R['addda']}+{L(c)}{R['capex']}+{L(c)}{R['dnwc']}", bold=True, indent=0); dc.total(R["ufcf"], C0 + 1, last)
    r += 1
    line("frac", "Fraction of year after the valuation date", None, lambda i, c: f"=MAX(0,MIN(1,({L(c)}5-{reg['val_date']})/365))", "factor", italic=True)
    line("ufcf_p", "Unlevered free cash flow in period", None, lambda i, c: f"={L(c)}{R['ufcf']}*{L(c)}{R['frac']}")
    line("per", "Discount period (years)", None, lambda i, c: f"=SUM(${L(cols[0])}${R['frac']}:{L(c)}{R['frac']})-{reg['midyear']}*{L(c)}{R['frac']}/2", "factor", italic=True)
    line("df", "Discount factor", None, lambda i, c: f"=1/(1+{reg['wacc']})^{L(c)}{R['per']}", "factor", italic=True)
    line("pv", "Present value of unlevered free cash flow", None, lambda i, c: f"={L(c)}{R['ufcf_p']}*{L(c)}{R['df']}", bold=True, indent=0)
    r += 1; dc.header(r, 2, 5, "Valuation at the midpoint assumptions"); r += 1
    dc.colhead(r, 4, "Perpetuity growth"); dc.colhead(r, 5, "Exit multiple"); dc.ws.row_dimensions[r].height = 28; r += 1
    LC = L(last); rng = lambda k: f"{L(cols[0])}{R[k]}:{LC}{R[k]}"
    def two(label, f_perp, f_exit, fmt, key=None, bold=False, note=None):
        nonlocal r
        dc.label(r, label, bold=bold, indent=0 if bold else 1)
        if f_perp is not None: a1 = dc.put(r, 4, f_perp, fmt, bold=bold)
        if f_exit is not None: a2 = dc.put(r, 5, f_exit, fmt, bold=bold)
        if note: dc.ws.cell(row=r, column=10, value=note).font = Font(italic=True, size=9, color=GREY)
        if key:
            if f_perp is not None: reg[key + "_perp"] = dc.a(r, 4)
            if f_exit is not None: reg[key + "_exit"] = dc.a(r, 5)
        r += 1; return r - 1
    rw = two("WACC", f"={reg['wacc']}", f"={reg['wacc']}", "pct", "wacc_dcf")
    rg = two("Perpetuity growth rate / exit multiple", f"={reg['g_mid']}", f"={reg['exit_mid']}", "pct")
    dc.ws.cell(row=rg, column=5).number_format = FMT["x"]
    rs = two("Sum of PV of unlevered free cash flow", f"=SUM({rng('pv')})", f"=SUM({rng('pv')})", "mm")
    rn = two("Terminal value discount period (years)", f"=SUM({rng('frac')})", f"=SUM({rng('frac')})", "factor", note="end of the final projection year")
    rtv = two("Terminal value", f"={LC}{R['ufcf']}*(1+D{rg})/(D{rw}-D{rg})", f"={LC}{R['ebitda']}*E{rg}", "mm", "tv", note="perpetuity: final-year UFCF × (1 + g) / (WACC - g); exit: final-year EBITDA × multiple")
    rpv = two("PV of terminal value", f"=D{rtv}/(1+D{rw})^D{rn}", f"=E{rtv}/(1+E{rw})^E{rn}", "mm")
    rev = two("Enterprise value", f"=D{rs}+D{rpv}", f"=E{rs}+E{rpv}", "mm", "ev", bold=True); dc.total(rev, 4, 5)
    two("PV of terminal value % of enterprise value", f"=D{rpv}/D{rev}", f"=E{rpv}/E{rev}", "pct", "tv_share")
    two("Implied exit multiple / implied perpetuity growth", f"=D{rtv}/{LC}{R['ebitda']}", f"=(E{rtv}*E{rw}-{LC}{R['ufcf']})/(E{rtv}+{LC}{R['ufcf']})", "x", "implied", note="cross-check of each method against the other")
    dc.ws.cell(row=r - 1, column=5).number_format = FMT["pct"]
    r += 1
    rd = two("Less: total debt", f"=-{reg['debt']}", f"=-{reg['debt']}", "mm"); rc = two("Plus: cash and short-term investments", f"={reg['cash']}", f"={reg['cash']}", "mm")
    rnci = two("Less: noncontrolling interests and preferred", f"=-({reg['nci']}+{reg['pref']})", f"=-({reg['nci']}+{reg['pref']})", "mm")
    radj_d = two("Net adjustments", f"=SUM(D{rd}:D{rnci})", f"=SUM(E{rd}:E{rnci})", "mm", bold=True); dc.total(radj_d, 4, 5); reg["net_adj"] = dc.a(radj_d, 4)
    req_d = two("Equity value", f"=D{rev}+D{radj_d}", f"=E{rev}+E{radj_d}", "mm", "equity", bold=True)
    two("Implied value per share", f"=D{req_d}/{reg['shares']}", f"=E{req_d}/{reg['shares']}", "ps", "dcf_ps_mid", bold=True)
    r += 1; dc.header(r, 2, 5, "Reverse DCF: what the unaffected price implies (at the midpoint WACC)"); r += 1
    def one(label, f, fmt, key, bold=False, note=None):
        nonlocal r
        dc.label(r, label, bold=bold, indent=0 if bold else 1); reg[key] = dc.put(r, 4, f, fmt, bold=bold)
        if note: dc.ws.cell(row=r, column=10, value=note).font = Font(italic=True, size=9, color=GREY)
        r += 1; return r - 1
    ru = one("Enterprise value at the unaffected price", f"={reg['px_unaff']}*{reg['shares']}-D{radj_d}", "mm", "rdcf_ev")
    rpt = one("Less: PV of projected unlevered free cash flow", f"=-D{rs}", "mm", "rdcf_pvcf")
    rtt = one("Terminal value the price requires", f"=(D{ru}+D{rpt})*(1+D{rw})^D{rn}", "mm", "rdcf_tv", note="undiscounted, at the end of the final projection year")
    one("Implied perpetuity growth rate", f"=(D{rtt}*D{rw}-{LC}{R['ufcf']})/(D{rtt}+{LC}{R['ufcf']})", "pct", "rdcf_g", bold=True, note="compare with the perpetuity growth rate assumed; a gap means the projections and the market disagree")
    one("Implied exit multiple (EV / final-year EBITDA)", f"=D{rtt}/{LC}{R['ebitda']}", "x", "rdcf_x", bold=True, note="compare with the exit multiple assumed")
    dc.ws.freeze_panes = "C6"
    reg.update({k: dc.a(R[k], last) for k in ("ufcf", "ebitda")}); reg["ufcf_N"], reg["ebitda_N"] = reg.pop("ufcf"), reg.pop("ebitda")
    reg["ebitda_fy1"] = dc.a(R["ebitda"], cols[0]); reg["tv_period"] = dc.a(rn, 4)
    reg["dcf_years"] = f"DCF!{L(C0)}4:{LC}4"
    for k in ("g", "m", "ebit", "tax", "capex", "dnwc", "addda", "ufcf_p", "per", "df"): reg[f"row_{k}"] = f"DCF!{L(C0)}{R[k]}:{LC}{R[k]}"
    for k in ("rev", "ebitda", "ufcf", "pv"): reg[f"row_{k}"] = f"DCF!{L(C0)}{R[k]}:{LC}{R[k]}"
    # fill the Comps net adjustments now that the DCF address exists
    for c in (4, 5): cell = cp.ws.cell(row=radj, column=c, value=f"={reg['net_adj']}"); cell.font = Font(color=GREEN, size=10); cell.number_format = FMT["mm"]

    # ---------------- LBO ----------------
    lb = Tab(wb, "LBO", "Leveraged Buyout Analysis (sponsor ability to pay)", {"A": 2, "B": 44, **{L(c): 12 for c in range(3, 9)}, "J": 50}); tabs["LBO"] = lb
    r = 4; lb.header(r, 2, 4, "Financing"); r += 1
    def ll(label, f, fmt, key=None, bold=False, note="", col=3):
        nonlocal r
        lb.label(r, label, bold=bold, indent=0 if bold else 1); addr = lb.put(r, col, f, fmt, bold=bold)
        if note: lb.ws.cell(row=r, column=10, value=note).font = Font(italic=True, size=9, color=GREY)
        if key: reg[key] = addr
        r += 1; return lb.loc(r - 1, col)
    l_eb = ll("LTM EBITDA", f"={reg['h_ebitda_ltm']}", "mm"); l_lev = ll("Total leverage (x LTM EBITDA)", f"={reg['lbo_lev']}", "x")
    l_debt = ll("New debt raised", f"={l_eb}*{l_lev}", "mm", bold=True); l_rate = ll("Blended interest rate", f"={reg['lbo_rate']}", "pct")
    l_tax = ll("Tax rate", f"={reg['tax_m']}", "pct"); l_exit = ll("Exit multiple (EV / EBITDA)", f"={reg['lbo_exit']}", "x"); l_hold = ll("Holding period (years)", f"={reg['hold']}", "int")
    l_fee = ll("Fees and expenses (% of EV)", f"={reg['lbo_fees']}", "pct")
    r += 1; lb.header(r, 2, 8, "Cash flow available for debt paydown"); r += 1
    for i, c in enumerate(cols): lb.put(r, c, f"=DCF!{L(c)}4", "yearE", bold=True, align="center")
    r += 1; LR = {}
    def lline(key, label, f, fmt="mm", bold=False):
        nonlocal r
        lb.label(r, label, bold=bold, indent=0 if bold else 1)
        for i, c in enumerate(cols): lb.put(r, c, f(i, c), fmt, bold=bold)
        LR[key] = r; r += 1
    lline("ebitda", "EBITDA", lambda i, c: f"=DCF!{L(c)}{R['ebitda']}")
    lline("ufcf", "Unlevered free cash flow (full year)", lambda i, c: f"=DCF!{L(c)}{R['ufcf']}")
    lline("int", "Less: after-tax interest", lambda i, c: f"=-{l_debt}*{l_rate}*(1-{l_tax})")
    lline("lfcf", "Levered free cash flow", lambda i, c: f"={L(c)}{LR['ufcf']}+{L(c)}{LR['int']}", bold=True); lb.total(LR["lfcf"], cols[0], last)
    lline("cum", "Cumulative debt paydown", lambda i, c: f"=SUM(${L(cols[0])}${LR['lfcf']}:{L(c)}{LR['lfcf']})")
    lb.ws.cell(row=r, column=2, value="Interest is charged on the opening debt balance throughout (no paydown credit), which is conservative and avoids a circular reference.").font = Font(italic=True, size=9, color=GREY); r += 2
    lb.header(r, 2, 5, "Exit and implied entry price"); r += 1
    lb.colhead(r, 4, "Low IRR"); lb.colhead(r, 5, "High IRR"); r += 1
    def l2(label, f1, f2, fmt, key=None, bold=False):
        nonlocal r
        lb.label(r, label, bold=bold, indent=0 if bold else 1); lb.put(r, 4, f1, fmt, bold=bold); lb.put(r, 5, f2, fmt, bold=bold)
        if key: reg[key + "_a"] = lb.a(r, 4); reg[key + "_b"] = lb.a(r, 5)
        r += 1; return r - 1
    ri = l2("Target IRR", f"={reg['irr_lo']}", f"={reg['irr_hi']}", "pct")
    rx = l2("Exit enterprise value", f"={LC}{LR['ebitda']}*{l_exit}", f"={LC}{LR['ebitda']}*{l_exit}", "mm")
    rxd = l2("Less: debt outstanding at exit", f"=-({l_debt}-{LC}{LR['cum']})", f"=-({l_debt}-{LC}{LR['cum']})", "mm")
    rxe = l2("Exit equity value", f"=D{rx}+D{rxd}", f"=E{rx}+E{rxd}", "mm", bold=True)
    ree = l2("Sponsor equity at entry (discounted at the IRR)", f"=D{rxe}/(1+D{ri})^{l_hold}", f"=E{rxe}/(1+E{ri})^{l_hold}", "mm")
    rev2 = l2("Implied entry enterprise value", f"=(D{ree}+{l_debt})/(1+{l_fee})", f"=(E{ree}+{l_debt})/(1+{l_fee})", "mm", bold=True)
    l2("Implied EV / LTM EBITDA", f"=D{rev2}/{l_eb}", f"=E{rev2}/{l_eb}", "x", "lbo_mult")
    rq = l2("Implied equity value", f"=D{rev2}+{reg['net_adj']}", f"=E{rev2}+{reg['net_adj']}", "mm")
    l2("Implied value per share", f"=D{rq}/{reg['shares']}", f"=E{rq}/{reg['shares']}", "ps", "lbo_ps", bold=True)
    reg["lbo_ps_hi"], reg["lbo_ps_lo"] = reg.pop("lbo_ps_a"), reg.pop("lbo_ps_b")     # the low IRR gives the high price
    reg["lbo_debt"] = f"LBO!${l_debt[0]}${l_debt[1:]}"

    # ---------------- Sensitivity ----------------
    se = Tab(wb, "Sensitivity", "Discounted Cash Flow Sensitivity — Implied Value per Share", {"A": 2, "B": 30, **{L(c): 12 for c in range(3, 9)}}); tabs["Sensitivity"] = se
    pvsum = lambda w: f"SUMPRODUCT(DCF!${L(cols[0])}${R['ufcf_p']}:${LC}${R['ufcf_p']},1/(1+{w})^DCF!${L(cols[0])}${R['per']}:${LC}${R['per']})"
    tail = f"+{reg['net_adj']})/{reg['shares']}"
    def grid(r, title, col_label, mid, step, fmt, tv):
        se.header(r, 2, 8, title); r += 1
        se.ws.cell(row=r, column=4, value=col_label).font = Font(bold=True, size=10); se.ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=8)
        se.ws.cell(row=r, column=4).alignment = Alignment(horizontal="center"); r += 1
        hr = r; se.label(hr, "WACC", bold=True); se.ws.cell(row=hr, column=2).alignment = Alignment(horizontal="right")
        for k, c in enumerate(range(4, 9)): se.put(hr, c, f"={mid}+({k - 2})*{step}", fmt, bold=True, align="center"); se.ws.cell(row=hr, column=c).border = Border(bottom=THIN)
        for k in range(5):
            rr = hr + 1 + k; se.put(rr, 3, f"={reg['wacc']}+({k - 2})*{reg['wacc_step']}", "pct", bold=True)
            for c in range(4, 9):
                w = f"$C{rr}"; x = f"{L(c)}${hr}"
                se.put(rr, c, f"=({pvsum(w)}+{tv(w, x)}/(1+{w})^{reg['tv_period']}{tail}", "ps")
            for c in range(4, 9):
                if k == 2 and c == 6: se.ws.cell(row=rr, column=c).fill = PatternFill("solid", fgColor="DDEBF7"); se.ws.cell(row=rr, column=c).font = Font(bold=True, size=10, color=GREEN)
        return hr
    hr1 = grid(4, "Perpetuity growth method", "Perpetuity growth rate", reg["g_mid"], reg["g_step"], "pct", lambda w, g: f"{reg['ufcf_N']}*(1+{g})/({w}-{g})")
    hr2 = grid(hr1 + 8, "Exit multiple method", "Exit multiple (EV / EBITDA)", reg["exit_mid"], reg["exit_step"], "x", lambda w, m: f"{reg['ebitda_N']}*{m}")
    r = hr2 + 8; se.header(r, 2, 5, "Selected ranges (midpoint WACC ± one step; terminal assumption ± one step)"); r += 1
    se.colhead(r, 4, "Low"); se.colhead(r, 5, "High"); r += 1
    se.label(r, "Perpetuity growth method", indent=1); reg["dcf_pgr_lo"] = se.put(r, 4, f"=E{hr1 + 4}", "ps"); reg["dcf_pgr_hi"] = se.put(r, 5, f"=G{hr1 + 2}", "ps"); r += 1
    se.label(r, "Exit multiple method", indent=1); reg["dcf_exit_lo"] = se.put(r, 4, f"=E{hr2 + 4}", "ps"); reg["dcf_exit_hi"] = se.put(r, 5, f"=G{hr2 + 2}", "ps"); r += 1
    se.ws.cell(row=r + 1, column=2, value="Low = WACC one step above the midpoint with the terminal assumption one step below; high = the reverse. The shaded cell is the midpoint, equal to the DCF tab.").font = Font(italic=True, size=9, color=GREY)
    reg["sens_pgr"] = f"Sensitivity!C{hr1}:H{hr1 + 5}"; reg["sens_exit"] = f"Sensitivity!C{hr2}:H{hr2 + 5}"
    reg["sens_pgr_mid"] = se.a(hr1 + 3, 6); reg["sens_exit_mid"] = se.a(hr2 + 3, 6)

    # ---------------- Summary ----------------
    sm = Tab(wb, "Summary", "Summary of Financial Analyses", {"A": 2, "B": 44, "C": 13, "D": 13, "E": 13, "F": 60}); tabs["Summary"] = sm
    r = 4; sm.header(r, 2, 4, "Transaction overview"); r += 1
    def so(label, f, fmt, key, bold=False):
        nonlocal r
        sm.label(r, label, indent=0 if bold else 1, bold=bold); reg[key] = sm.put(r, 3, f, fmt, bold=bold); r += 1; return sm.loc(r - 1, 3)
    s_off = so("Offer price per share", f"={reg['px_offer']}", "ps", "s_offer", bold=True)
    so("Premium to unaffected price", f"={s_off}/{reg['px_unaff']}-1", "pct", "prem_unaff"); so("Premium to 30-trading-day average", f"={s_off}/{reg['px_30d']}-1", "pct", "prem_30d")
    so("Premium (discount) to 52-week high", f"={s_off}/{reg['px_hi']}-1", "pct", "prem_hi52")
    s_eq = so("Implied equity value", f"={s_off}*{reg['shares']}", "mm", "offer_equity"); s_ev = so("Implied enterprise value", f"={s_eq}-{reg['net_adj']}", "mm", "offer_ev")
    so("Implied EV / LTM revenue", f"={s_ev}/{reg['h_rev_ltm']}", "x", "offer_ev_rev"); so("Implied EV / LTM EBITDA", f"={s_ev}/{reg['h_ebitda_ltm']}", "x", "offer_ev_ebitda")
    so(f"Implied EV / FY{A[-1]['fy'] + 1}E EBITDA", f"={s_ev}/{reg['ebitda_fy1']}", "x", "offer_ev_fy1")
    r += 1; sm.header(r, 2, 6, "Implied value per share"); r += 1
    sm.colhead(r, 3, "Low"); sm.colhead(r, 4, "High"); sm.colhead(r, 5, "Spread"); sm.colhead(r, 6, "Basis"); r += 1; ff0 = r
    ff = [("52-week trading range (reference)", f"={reg['px_lo']}", f"={reg['px_hi']}", "52-week low and high closing prices", "trading_range"),
          ("Premiums paid (illustrative)", f"={reg['px_unaff']}*(1+{reg['prem_lo']})", f"={reg['px_unaff']}*(1+{reg['prem_hi']})", "premium range applied to the unaffected price", "premiums"),
          ("Selected public companies", f"={reg['comps_ps_lo']}", f"={reg['comps_ps_hi']}", "selected EV / LTM EBITDA range", "comps"),
          ("Discounted cash flow — perpetuity growth", f"={reg['dcf_pgr_lo']}", f"={reg['dcf_pgr_hi']}", "WACC and perpetuity growth ranges", "dcf_pgr"),
          ("Discounted cash flow — exit multiple", f"={reg['dcf_exit_lo']}", f"={reg['dcf_exit_hi']}", "WACC and exit multiple ranges", "dcf_exit"),
          ("Leveraged buyout", f"={reg['lbo_ps_lo']}", f"={reg['lbo_ps_hi']}", "target IRR range", "lbo")]
    for label, lo, hi, basis, key in ff:
        sm.label(r, label, indent=1); reg[f"ff_{key}_lo"] = sm.put(r, 3, lo, "ps"); reg[f"ff_{key}_hi"] = sm.put(r, 4, hi, "ps"); sm.put(r, 5, f"=D{r}-C{r}", "ps")
        sm.ws.cell(row=r, column=6, value=basis).font = Font(italic=True, size=9, color=GREY); r += 1
    ffN = r - 1; sm.total(r, 2, 5); sm.label(r, "Offer price per share", bold=True); sm.put(r, 3, f"={s_off}", "ps", bold=True)
    ch = BarChart(); ch.type = "bar"; ch.grouping = "stacked"; ch.overlap = 100; ch.title = "Implied value per share"; ch.legend = None; ch.height = 7.5; ch.width = 18
    data = Reference(sm.ws, min_col=3, min_row=ff0, max_row=ffN); spread = Reference(sm.ws, min_col=5, min_row=ff0, max_row=ffN); cats = Reference(sm.ws, min_col=2, min_row=ff0, max_row=ffN)
    ch.add_data(data, titles_from_data=False); ch.add_data(spread, titles_from_data=False); ch.set_categories(cats)
    ch.series[0].graphicalProperties.noFill = True; ch.series[0].graphicalProperties.line.noFill = True; ch.series[1].graphicalProperties.solidFill = NAVY
    ch.y_axis.scaling.orientation = "minMax"; ch.x_axis.scaling.orientation = "maxMin"; ch.y_axis.numFmt = "$#,##0"; ch.y_axis.majorGridlines = None
    sm.ws.add_chart(ch, f"B{r + 3}")
    wb.calculation = CalcProperties(fullCalcOnLoad=True)
    wb._sheets = [wb[n] for n in SHEETS]
    out = Path(out); out.mkdir(parents=True, exist_ok=True); p = out / "model.xlsx"; wb.save(p)
    return p, reg, D

def recalc(xlsx):
    """Recalculate in headless LibreOffice and return the path of a copy that carries the computed values."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice") or ("/Applications/LibreOffice.app/Contents/MacOS/soffice" if Path("/Applications/LibreOffice.app").exists() else None)
    if not soffice: raise SystemExit("LibreOffice (soffice) is needed to recalculate the model headless: brew install --cask libreoffice")
    tmp = Path(tempfile.mkdtemp(prefix="recalc_")); prof = Path(tempfile.mkdtemp(prefix="lo_profile_"))
    subprocess.run([soffice, f"-env:UserInstallation=file://{prof}", "--headless", "--calc", "--convert-to", "xlsx:Calc MS Excel 2007 XML", "--outdir", str(tmp), str(xlsx)], capture_output=True, text=True, timeout=180)
    got = tmp / Path(xlsx).name
    if not got.exists(): raise SystemExit("LibreOffice did not produce a recalculated copy")
    return got

def read_values(xlsx_calc, reg):
    wb = load_workbook(xlsx_calc, data_only=True)
    def val(addr):
        sh, ref = addr.split("!"); ref = ref.replace("$", "")
        if ":" in ref:
            rows = wb[sh][ref]; return [[c.value for c in row] for row in rows]
        return wb[sh][ref].value
    return {k: {"value": val(v), "cell": v} for k, v in reg.items() if isinstance(v, str) and "!" in v}, wb

def errors(wb):
    bad = []
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("#") and c.value.rstrip("!?0/").upper() in ("#DIV", "#REF", "#NAME", "#VALUE", "#N/A", "#NUM", "#NULL", "#DIV/"): bad.append(f"{ws.title}!{c.coordinate} {c.value}")
                elif isinstance(c.value, str) and c.value in ("#DIV/0!", "#REF!", "#NAME?", "#VALUE!", "#N/A", "#NUM!", "Err:502", "Err:504", "Err:522"): bad.append(f"{ws.title}!{c.coordinate} {c.value}")
    return sorted(set(bad))

def sanity(v):
    """Reviewer flags: values a banker would question before the deck goes out. Flags, not failures."""
    g = lambda k: (v.get(k) or {}).get("value"); F = []
    w = g("wacc")
    if isinstance(w, (int, float)) and not 0.05 <= w <= 0.15: F.append(f"WACC {w:.1%} is outside 5%-15%")
    ts = g("tv_share_perp")
    if isinstance(ts, (int, float)) and ts > 0.85: F.append(f"terminal value is {ts:.0%} of DCF enterprise value (perpetuity method)")
    im = g("implied_perp")
    if isinstance(im, (int, float)) and not 4 <= im <= 25: F.append(f"perpetuity method implies a {im:.1f}x exit multiple")
    ig = g("implied_exit")
    if isinstance(ig, (int, float)) and not -0.01 <= ig <= 0.05: F.append(f"exit multiple method implies {ig:.1%} perpetuity growth")
    tm, q1, q3 = g("tgt_ev_ltm_ebitda_unaff"), g("comps_q1_ebitda"), g("comps_q3_ebitda")
    if all(isinstance(x, (int, float)) for x in (tm, q1, q3)) and (tm > q3 * 1.15 or tm < q1 * 0.85):
        F.append(f"the target trades at {tm:.1f}x LTM EBITDA, outside the peers' {q1:.1f}x-{q3:.1f}x interquartile range: the peer set may not be comparable (name peers with --peers)")
    npeers = len([r for r in (g("comps_table") or []) if r and r[0]])
    if npeers < 3: F.append(f"only {npeers} peer(s): too few for a selected public companies analysis; name peers with --peers")
    px = g("px_unaff"); intrinsic = [((g(f"ff_{k}_lo") or 0) + (g(f"ff_{k}_hi") or 0)) / 2 for k in ("comps", "dcf_pgr", "dcf_exit")]
    if isinstance(px, (int, float)) and px > 0:
        far = [m for m in intrinsic if abs(m / px - 1) > 0.30]
        rg, rx = g("rdcf_g"), g("rdcf_x")
        rev = f" (reverse DCF: the unaffected price implies {rg:.1%} perpetuity growth or a {rx:.1f}x exit multiple)" if isinstance(rg, (int, float)) and isinstance(rx, (int, float)) else ""
        if len(far) >= 2: F.append(f"the comps and DCF midpoints ({', '.join(f'${m:,.2f}' for m in intrinsic)}) sit more than 30% from the unaffected price of ${px:,.2f}: the projections or the peers likely do not reflect what the market prices in; review both before relying on a 'fair' result{rev}")
    for k in ("trading_range", "premiums", "comps", "dcf_pgr", "dcf_exit", "lbo"):
        lo, hi = g(f"ff_{k}_lo"), g(f"ff_{k}_hi")
        if not isinstance(lo, (int, float)) or not isinstance(hi, (int, float)): F.append(f"{k}: no numeric range"); continue
        if lo > hi: F.append(f"{k}: low {lo:.2f} above high {hi:.2f}")
        if lo <= 0: F.append(f"{k}: non-positive value per share ({lo:.2f})")
    return F

def evaluate(model, reg, co, D, out, log=print):
    """Recalculate a model (freshly built or edited by hand) and write valuation.json from its cells."""
    calc = recalc(model); vals, wb = read_values(calc, reg); errs = errors(wb)
    shutil.copy(calc, Path(out) / "model_values.xlsx")
    flags = sanity(vals); num = lambda k: vals[k]["value"]
    ranges = {k: {"low": num(f"ff_{k}_lo"), "high": num(f"ff_{k}_hi")} for k in ("trading_range", "premiums", "comps", "dcf_pgr", "dcf_exit", "lbo")}
    doc = {"schema": SCHEMAS["valuation"], "ticker": co["target"]["ticker"], "target": co["target"]["name"], "model": str(model), "model_values": str(Path(out) / "model_values.xlsx"),
           "synthetic": bool(co.get("synthetic")), "ranges": ranges, "cells": vals, "assumption_basis": D["basis"], "errors": errs, "flags": flags,
           "peers": [{"name": x["name"], "ticker": x["ticker"]} for x in co["peers"]], "peer_basis": co["peer_basis"], "as_of": co["as_of"]}
    vp = save(doc, Path(out) / "valuation.json"); log(f"wrote {vp}")
    log("ranges ($/share): " + "; ".join(f"{k} {v['low']:.2f}-{v['high']:.2f}" if isinstance(v['low'], (int, float)) and isinstance(v['high'], (int, float)) else f"{k} n/a" for k, v in ranges.items()))
    if errs: log(f"FORMULA ERRORS ({len(errs)}): {errs[:10]}")
    for f in flags: log(f"flag: {f}")
    return doc

def run(company_json, terms_json, out, log=print):
    co = need(load(company_json), "company", company_json); terms = need(load(terms_json), "deal_terms", terms_json)
    p, reg, D = build(co, terms, out); log(f"wrote {p}")
    return evaluate(p, reg, co, D, out, log)

def revalue(company_json, valuation_json, log=print):
    """After the user edits model.xlsx by hand (an assumption, a peer's data): recalculate it and refresh valuation.json, keeping the edits."""
    co = need(load(company_json), "company", company_json); old = need(load(valuation_json), "valuation", valuation_json)
    reg = {k: v["cell"] for k, v in old["cells"].items()}
    return evaluate(Path(old["model"]), reg, co, {"basis": old["assumption_basis"]}, Path(valuation_json).parent, log)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("company"); ap.add_argument("terms"); ap.add_argument("out"); a = ap.parse_args()
    d = run(a.company, a.terms, a.out); sys.exit(1 if d["errors"] else 0)
