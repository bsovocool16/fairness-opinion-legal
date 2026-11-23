#!/usr/bin/env python3
"""Stage 3 of the ticker-to-proxy lifecycle: the board book, from the recalculated model.

  python3 build_deck.py <company.json> <deal_terms.json> <valuation.json> <out dir>    writes board_book.pptx, board_book.pdf, deck.json

Every number on a slide is read from valuation.json, which build_model.py read back from the recalculated workbook, so the
book cannot disagree with the model. Slide titles use the names the board-book classifier (scripts/analyses.py DECK_RX)
recognizes, and the book avoids naming analyses it does not contain (no precedent transactions, no analyst price targets).
The PDF goes through LibreOffice and keeps a text layer, so intake needs no OCR."""
import sys, shutil, subprocess, tempfile, datetime, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load, save, need, SCHEMAS, disclaimer, STATES
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION

NAVY = RGBColor(0x1F, 0x38, 0x64); GREY = RGBColor(0x80, 0x80, 0x80); LIGHT = RGBColor(0xDD, 0xEB, 0xF7); RED = RGBColor(0xC0, 0x00, 0x00); WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BLACK = RGBColor(0, 0, 0); GOLD = RGBColor(0xC9, 0x8B, 0x00)
W, H = Inches(13.333), Inches(7.5)

def money(x, d=2): return "NM" if not isinstance(x, (int, float)) else (f"(${-x:,.{d}f})" if x < 0 else f"${x:,.{d}f}")
def mmf(x, d=1): return "NM" if not isinstance(x, (int, float)) else (f"({-x:,.{d}f})" if x < 0 else f"{x:,.{d}f}")
def pct(x, d=1): return "NM" if not isinstance(x, (int, float)) else (f"({-x * 100:.{d}f}%)" if x < 0 else f"{x * 100:.{d}f}%")
def mult(x): return "NM" if not isinstance(x, (int, float)) else f"{x:.1f}x"

class Deck:
    def __init__(self, terms, target):
        self.p = Presentation(); self.p.slide_width, self.p.slide_height = W, H; self.blank = self.p.slide_layouts[6]
        self.terms, self.target, self.n, self.index = terms, target, 0, []
        self.foot = disclaimer(terms["advisor"], target)
    def text(self, s, x, y, w, h, t, size=12, bold=False, color=BLACK, align=PP_ALIGN.LEFT, italic=False, anchor=MSO_ANCHOR.TOP):
        tb = s.shapes.add_textbox(x, y, w, h); tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
        for i, line in enumerate(t if isinstance(t, list) else [t]):
            para = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); para.alignment = align
            run = para.add_run(); run.text = line; f = run.font; f.size = Pt(size); f.bold = bold; f.italic = italic; f.color.rgb = color; f.name = "Arial"
        return tb
    def slide(self, title, analysis=None, subtitle=None):
        s = self.p.slides.add_slide(self.blank); self.n += 1
        self.text(s, Inches(0.5), Inches(0.3), Inches(10.8), Inches(0.6), title, 24, True, NAVY)   # the title is the page's first text line
        if subtitle: self.text(s, Inches(0.5), Inches(0.85), Inches(12), Inches(0.4), subtitle, 12, False, GREY, italic=True)
        bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(1.25), Inches(12.33), Emu(22000)); bar.fill.solid(); bar.fill.fore_color.rgb = NAVY; bar.line.fill.background()
        st = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(11.3), Inches(0.3), Inches(1.55), Inches(0.42)); st.fill.background(); st.line.color.rgb = RED
        tf = st.text_frame; tf.paragraphs[0].alignment = PP_ALIGN.CENTER; r = tf.paragraphs[0].add_run(); r.text = "ILLUSTRATIVE"; r.font.size = Pt(11); r.font.bold = True; r.font.color.rgb = RED
        self.text(s, Inches(0.5), Inches(6.95), Inches(11.6), Inches(0.45), self.foot, 7, False, GREY, italic=True)
        self.text(s, Inches(12.3), Inches(7.0), Inches(0.6), Inches(0.3), str(self.n), 9, False, GREY, PP_ALIGN.RIGHT)
        self.index.append({"page": self.n, "title": title, "analysis": analysis}); return s
    def table(self, s, rows, x, y, w, colw=None, size=10, head=1, bold_rows=(), shade_rows=(), rowh=0.28, align_first=PP_ALIGN.LEFT):
        nr, nc = len(rows), len(rows[0]); tb = s.shapes.add_table(nr, nc, x, y, w, Inches(rowh * nr)).table
        if colw:
            tot = sum(colw)
            for i, cw in enumerate(colw): tb.columns[i].width = int(w * cw / tot)
        for i, row in enumerate(rows):
            tb.rows[i].height = Inches(rowh)
            for j, v in enumerate(row):
                c = tb.cell(i, j); c.text = "" if v is None else str(v); c.margin_left = c.margin_right = Inches(0.05); c.margin_top = c.margin_bottom = Inches(0.02)
                para = c.text_frame.paragraphs[0]; para.alignment = align_first if j == 0 else PP_ALIGN.CENTER
                for run in para.runs:
                    run.font.size = Pt(size); run.font.name = "Arial"; run.font.bold = i < head or i in bold_rows; run.font.color.rgb = WHITE if i < head else BLACK
                c.fill.solid(); c.fill.fore_color.rgb = NAVY if i < head else (LIGHT if i in shade_rows else WHITE)
        return tb
    def notes(self, s, lines, y=Inches(5.9), size=9):
        return self.text(s, Inches(0.5), y, Inches(12.3), Inches(1.0), lines, size, False, GREY, italic=True)

def run(company_json, terms_json, valuation_json, out, log=print):
    co = need(load(company_json), "company", company_json); terms = need(load(terms_json), "deal_terms", terms_json); val = need(load(valuation_json), "valuation", valuation_json)
    t = co["target"]; C = val["cells"]; g = lambda k: C[k]["value"]; R = val["ranges"]
    d = Deck(terms, t["name"]); date = datetime.date.fromisoformat(terms["opinion_date"]).strftime("%B %-d, %Y")
    offer = g("s_offer")
    # 1 cover
    s = d.p.slides.add_slide(d.blank); d.n += 1; d.index.append({"page": 1, "title": "Cover", "analysis": None})
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, Inches(4.2)); bg.fill.solid(); bg.fill.fore_color.rgb = NAVY; bg.line.fill.background()
    d.text(s, Inches(0.8), Inches(1.2), Inches(11.5), Inches(0.8), terms.get("codename") or "Project", 36, True, WHITE)
    d.text(s, Inches(0.8), Inches(2.1), Inches(11.5), Inches(1.2), ["Discussion Materials", f"Prepared for {terms['addressee']} of {t['name']}"], 20, False, WHITE)
    d.text(s, Inches(0.8), Inches(4.6), Inches(11.5), Inches(0.5), date, 16, False, NAVY)
    d.text(s, Inches(0.8), Inches(5.2), Inches(11.5), Inches(0.5), f"Illustrative materials in the form a financial advisor ({terms['advisor']}) would present", 12, False, GREY, italic=True)
    d.text(s, Inches(0.8), Inches(6.3), Inches(11.8), Inches(0.8), d.foot, 9, True, RED)
    # 2 transaction overview
    s = d.slide("Transaction Overview", None, f"Hypothetical acquisition of {t['name']} by {terms['buyer']}")
    rows = [["Proposed transaction", ""], ["Offer price per share", money(offer)], ["Consideration", terms["consideration"].capitalize()],
            ["Premium to unaffected price " + f"({money(g('px_unaff'))} on {terms['unaffected_date']})", pct(g("prem_unaff"))],
            ["Premium to 30-trading-day average", pct(g("prem_30d"))], ["Premium (discount) to 52-week high", pct(g("prem_hi52"))],
            ["Implied equity value ($mm)", mmf(g("offer_equity"))], ["Implied enterprise value ($mm)", mmf(g("offer_ev"))],
            ["Implied EV / LTM revenue", mult(g("offer_ev_rev"))], ["Implied EV / LTM EBITDA", mult(g("offer_ev_ebitda"))], ["Implied EV / next fiscal year EBITDA (illustrative projections)", mult(g("offer_ev_fy1"))]]
    d.table(s, rows, Inches(0.5), Inches(1.6), Inches(8.2), [5, 2], 12, rowh=0.36)
    d.text(s, Inches(9.1), Inches(1.6), Inches(3.8), Inches(3.5), [f"Buyer: {terms['buyer']} ({terms['buyer_type']})", f"Transaction type: {'Rule 13e-3 going-private' if terms['regime'] == '13e-3' else 'third-party acquisition'}",
            f"Shares outstanding: {g('shares'):,.1f} million", f"Valuation date: {date}", f"Market data as of {co['as_of']}"], 11, False, BLACK)
    d.notes(s, ["Implied enterprise value equals implied equity value plus total debt, noncontrolling interests and preferred stock, less cash and short-term investments, from the latest balance sheet filed with the SEC.",
                "LTM figures from SEC XBRL filings. Projections are illustrative, derived from reported history (see the valuation model, Assumptions tab); they are not management projections."])
    # 3 summary (football field)
    s = d.slide("Summary of Financial Analyses", "summary", "Implied value per share of common stock")
    items = [("Discounted Cash Flow Analysis — perpetuity growth", "dcf_pgr", f"WACC {pct(g('wacc') - g('wacc_step'))}–{pct(g('wacc') + g('wacc_step'))}; perpetuity growth {pct(g('g_mid') - g('g_step'))}–{pct(g('g_mid') + g('g_step'))}"),
             ("Discounted Cash Flow Analysis — exit multiple", "dcf_exit", f"WACC {pct(g('wacc') - g('wacc_step'))}–{pct(g('wacc') + g('wacc_step'))}; exit multiples {mult(g('exit_mid') - g('exit_step'))}–{mult(g('exit_mid') + g('exit_step'))} EBITDA"),
             ("Selected Public Companies Analysis", "comps", f"{mult(g('comps_lo'))}–{mult(g('comps_hi'))} EV / LTM EBITDA"),
             ("Leveraged Buyout Analysis", "lbo", f"{pct(g('irr_lo'), 0)}–{pct(g('irr_hi'), 0)} target IRR; {mult(g('lbo_lev'))} leverage; {mult(g('lbo_exit'))} exit"),
             ("Premiums Paid Analysis (illustrative)", "premiums", f"{pct(g('prem_lo'), 0)}–{pct(g('prem_hi'), 0)} premium to unaffected price"),
             ("52-Week Trading Range (for reference only)", "trading_range", "52-week low and high closing prices")]
    lo_all = min(min(R[k]["low"], R[k]["high"]) for _, k, _ in items); hi_all = max(max(R[k]["low"], R[k]["high"]) for _, k, _ in items)
    lo_ax = max(0, (min(lo_all, offer) * 0.85) // 5 * 5); hi_ax = (max(hi_all, offer) * 1.1 // 5 + 1) * 5
    X0, X1 = Inches(5.3), Inches(12.6); Y0 = Inches(1.65); rowh = Inches(0.68)
    xp = lambda v: int(X0 + (X1 - X0) * (v - lo_ax) / (hi_ax - lo_ax))
    for i, (label, k, basis) in enumerate(items):
        y = Y0 + rowh * i; lo, hi = R[k]["low"], R[k]["high"]
        d.text(s, Inches(0.5), y, Inches(4.7), Inches(0.35), label, 11, True); d.text(s, Inches(0.5), y + Inches(0.28), Inches(4.7), Inches(0.35), basis, 8, False, GREY, italic=True)
        bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, xp(lo), y + Inches(0.08), max(xp(hi) - xp(lo), Emu(20000)), Inches(0.42)); bar.fill.solid(); bar.fill.fore_color.rgb = GREY if k == "trading_range" else NAVY; bar.line.fill.background()
        d.text(s, xp(lo) - Inches(0.95), y + Inches(0.1), Inches(0.9), Inches(0.35), money(lo), 10, False, BLACK, PP_ALIGN.RIGHT)
        d.text(s, xp(hi) + Inches(0.05), y + Inches(0.1), Inches(0.9), Inches(0.35), money(hi), 10, False, BLACK)
    ln = s.shapes.add_connector(1, xp(offer), Y0 - Inches(0.1), xp(offer), Y0 + rowh * len(items)); ln.line.color.rgb = RED; ln.line.width = Pt(2); ln.line.dash_style = 4
    d.text(s, xp(offer) - Inches(1.2), Y0 + rowh * len(items), Inches(2.4), Inches(0.35), f"Offer price: {money(offer)}", 11, True, RED, PP_ALIGN.CENTER)
    d.notes(s, ["The 52-week trading range is presented for reference only and is not a valuation methodology. Premiums paid range is illustrative.",
                "Implied values per share are rounded to the nearest $0.01 and are based on the illustrative projections and the assumptions in the valuation model."], Inches(6.25))
    # 3a the judgment calls: each EBITDA definition the data supports, each from its own recalculated workbook
    cases = val.get("cases") or {}
    if len(cases) > 1:
        s = d.slide("EBITDA Definition: Judgment Calls", None, "Implied value per share under each EBITDA definition; the base case is the first column")
        short = {"reported": "Reported (SBC as a cash cost)", "ex_sbc": "SBC added back", "management": "Management adjusted"}
        ks = [k for k in ("reported", "ex_sbc", "management") if k in cases]; cv = lambda k, c: (cases[k]["cells"].get(c) or {}).get("value")
        rng = lambda k, a: f"{money(cases[k]['ranges'][a]['low'])} – {money(cases[k]['ranges'][a]['high'])}"
        rows = [[""] + [short[k] for k in ks], ["LTM EBITDA ($mm)"] + [mmf(cv(k, "h_ebitda_ltm")) for k in ks],
                [f"{t['name']} EV / LTM EBITDA at the unaffected price"] + [mult(cv(k, "tgt_ev_ltm_ebitda_unaff")) for k in ks],
                ["Selected EV / LTM EBITDA multiples"] + [f"{mult(cv(k, 'comps_lo'))}–{mult(cv(k, 'comps_hi'))}" for k in ks], ["WACC (midpoint)"] + [pct(cv(k, "wacc")) for k in ks],
                ["Selected Public Companies Analysis"] + [rng(k, "comps") for k in ks], ["Discounted Cash Flow Analysis — perpetuity growth"] + [rng(k, "dcf_pgr") for k in ks],
                ["Discounted Cash Flow Analysis — exit multiple"] + [rng(k, "dcf_exit") for k in ks], ["Leveraged Buyout Analysis"] + [rng(k, "lbo") for k in ks],
                ["Offer price per share"] + [money(offer)] * len(ks)]
        d.table(s, rows, Inches(0.5), Inches(1.6), Inches(12.3), [5] + [3] * len(ks), 11, bold_rows=(len(rows) - 1,), rowh=0.38)
        d.notes(s, [cases[k]["label"] + "." for k in ks] + ["Trading range and premiums do not depend on the EBITDA definition. Each column is a separate model workbook (cases/<case>/model.xlsx)."], Inches(5.55))
    # 4 52-week trading range
    s = d.slide("52-Week Trading Range", "trading_range", f"{t['name']} daily closing share price, 52 weeks to {t['price']['date']} (for reference only)")
    hist = t["price"]["history_1y"]
    if hist:
        cd = CategoryChartData(); step = max(1, len(hist) // 120); pts = hist[::step]
        cd.categories = [datetime.date.fromisoformat(x[0]).strftime("%b %y") for x in pts]; cd.add_series("Closing price", [x[1] for x in pts])
        cd.add_series("Offer price", [offer] * len(pts))
        ch = s.shapes.add_chart(XL_CHART_TYPE.LINE, Inches(0.5), Inches(1.5), Inches(8.6), Inches(4.3), cd).chart
        ch.has_legend = True; ch.legend.position = XL_LEGEND_POSITION.BOTTOM; ch.legend.include_in_layout = False
        ch.series[0].format.line.color.rgb = NAVY; ch.series[1].format.line.color.rgb = RED; ch.series[0].smooth = False
        ch.value_axis.tick_labels.font.size = Pt(9); ch.category_axis.tick_labels.font.size = Pt(8); ch.value_axis.has_major_gridlines = False
        ch.value_axis.tick_labels.number_format = '"$"#,##0'; ch.value_axis.tick_labels.number_format_is_linked = False
    d.table(s, [["Share price statistics", ""], ["52-week high", money(g("px_hi"))], ["52-week low", money(g("px_lo"))], ["30-trading-day average", money(g("px_30d"))],
                ["Unaffected price", money(g("px_unaff"))], ["Offer price", money(offer)], ["Offer premium to 52-week high", pct(g("prem_hi52"))]], Inches(9.4), Inches(1.6), Inches(3.4), [3, 2], 11, rowh=0.38)
    d.notes(s, [f"Source: daily closing prices ({t['price']['source']}). Presented for reference only."])
    # 5 projections
    yrs = g("dcf_years")[0]; ylab = [f"{int(yrs[0])}A"] + [f"{int(y)}E" for y in yrs[1:]]
    rv, eb, uf = g("row_rev")[0], g("row_ebitda")[0], g("row_ufcf")[0]; gr, mg = g("row_g")[0], g("row_m")[0]
    s = d.slide("Illustrative Financial Projections", None, "($ in millions) — derived from reported history; not management projections")
    rows = [["Fiscal year"] + ylab, ["Revenue"] + [mmf(x) for x in rv], ["  % growth", ""] + [pct(x) for x in gr[1:]], ["EBITDA"] + [mmf(x) for x in eb], ["  % margin", ""] + [pct(x) for x in mg[1:]],
            ["Unlevered free cash flow", ""] + [mmf(x) for x in uf[1:]]]
    d.table(s, rows, Inches(0.5), Inches(1.6), Inches(12.3), [3] + [1] * len(ylab), 11, bold_rows=(1, 3, 5), rowh=0.38)
    b = val["assumption_basis"]
    d.notes(s, [f"Revenue growth: {b['growth']}.", f"EBITDA margin: {b['margin']}; D&A: {b['da']}; capital expenditures: {b['capex']}; net working capital: {b['nwc']}.",
                "Unlevered free cash flow = EBIT less taxes at 25%, plus D&A, less capital expenditures and the increase in net working capital. Stock-based compensation is treated as a cash expense (not added back)."], Inches(4.4), 10)
    # 6 selected public companies
    s = d.slide("Selected Public Companies Analysis", "comps", f"Peers: {co['peer_basis']}")
    hdr = ["Company", "Enterprise value ($mm)", "EV / LTM revenue", "EV / LTM EBITDA", "EV / LTM EBIT", "LTM EBITDA margin"]
    rows = [hdr] + [[r_[0], mmf(r_[8], 0), mult(r_[13]), mult(r_[14]), mult(r_[15]), pct(r_[16])] for r_ in g("comps_table")]
    stats = g("comps_stats"); labels = ["Maximum", "75th percentile", "Median", "Mean", "25th percentile", "Minimum"]
    keep = {"75th percentile", "Median", "25th percentile"}
    base = len(rows); rows += [[lab, "", mult(st[13]), mult(st[14]), mult(st[15]), pct(st[16])] for lab, st in zip(labels, stats) if lab in keep]
    tr = g("comps_target_row")[0]; rows += [[f"{t['name']} (at unaffected price)", mmf(tr[8], 0), mult(tr[13]), mult(tr[14]), mult(tr[15]), pct(tr[16])]]
    d.table(s, rows, Inches(0.5), Inches(1.5), Inches(8.8), [4, 1.6, 1.3, 1.3, 1.3, 1.3], 9, bold_rows=tuple(range(base, base + 3)), shade_rows=tuple(range(base, base + 3)), rowh=0.3)
    d.table(s, [["Implied value per share", ""], ["Selected EV / LTM EBITDA", f"{mult(g('comps_lo'))} – {mult(g('comps_hi'))}"], [f"{t['ticker']} LTM EBITDA ($mm)", mmf(g("h_ebitda_ltm"))],
                ["Implied value per share", f"{money(R['comps']['low'])} – {money(R['comps']['high'])}"], ["Offer price", money(offer)]], Inches(9.6), Inches(1.5), Inches(3.3), [2.2, 1.6], 10, bold_rows=(3,), rowh=0.4)
    d.notes(s, ["Enterprise value = equity value (share price × shares outstanding) plus debt, noncontrolling interests and preferred, less cash. Market data as of " + co["as_of"] + "; balance sheets and LTM results from each company's latest SEC filings.",
                "No company used in this analysis is identical to the Company. Multiples above the NM threshold or with negative denominators are shown as NM and excluded."], Inches(6.1))
    # 7 DCF
    s = d.slide("Discounted Cash Flow Analysis", "dcf", "($ in millions, except per-share data)")
    pv = g("row_pv")[0]
    rows = [["Fiscal year"] + ylab[1:], ["Unlevered free cash flow"] + [mmf(x) for x in uf[1:]], ["Cash flow in period (stub for first year)"] + [mmf(x) for x in g("row_ufcf_p")[0][1:]],
            ["Discount factor"] + [f"{x:.3f}" for x in g("row_df")[0][1:]], ["Present value"] + [mmf(x) for x in pv[1:]]]
    d.table(s, rows, Inches(0.5), Inches(1.5), Inches(8.0), [3] + [1] * (len(ylab) - 1), 10, bold_rows=(4,), rowh=0.34)
    rows = [["", "Perpetuity growth", "Exit multiple"], ["WACC (midpoint)", pct(g("wacc_dcf_perp")), pct(g("wacc_dcf_exit"))], ["Terminal assumption", pct(g("g_mid")), mult(g("exit_mid"))],
            ["Enterprise value ($mm)", mmf(g("ev_perp")), mmf(g("ev_exit"))], ["Terminal value % of EV", pct(g("tv_share_perp")), pct(g("tv_share_exit"))],
            ["Implied exit multiple / perpetuity growth", mult(g("implied_perp")), pct(g("implied_exit"))], ["Implied value per share (midpoint)", money(g("dcf_ps_mid_perp")), money(g("dcf_ps_mid_exit"))],
            ["Selected range per share", f"{money(R['dcf_pgr']['low'])} – {money(R['dcf_pgr']['high'])}", f"{money(R['dcf_exit']['low'])} – {money(R['dcf_exit']['high'])}"],
            [f"Reverse DCF: implied by the unaffected price ({money(g('px_unaff'))})", pct(g("rdcf_g")), mult(g("rdcf_x"))]]
    d.table(s, rows, Inches(0.5), Inches(3.3), Inches(8.0), [3, 1.6, 1.6], 10, bold_rows=(6, 7), shade_rows=(7,), rowh=0.3)
    d.text(s, Inches(8.9), Inches(1.5), Inches(4.0), Inches(4.2), ["Methodology", f"Unlevered free cash flows for the fiscal years {ylab[1]} through {ylab[-1]} discounted to {date} using a mid-year convention, with the first year prorated for the stub period.",
            f"Discount rates of {pct(g('wacc') - g('wacc_step'))} to {pct(g('wacc') + g('wacc_step'))}, based on a weighted average cost of capital of {pct(g('wacc'))} (see appendix).",
            f"Terminal value by perpetuity growth rates of {pct(g('g_mid') - g('g_step'))} to {pct(g('g_mid') + g('g_step'))}, and by exit multiples of {mult(g('exit_mid') - g('exit_step'))} to {mult(g('exit_mid') + g('exit_step'))} terminal-year EBITDA (selected public companies median {mult(g('comps_median_ebitda'))}; {t['ticker']} at the unaffected price {mult(g('tgt_ev_ltm_ebitda_unaff'))} LTM EBITDA).",
            f"Reverse DCF: at the midpoint WACC, the unaffected price implies {pct(g('rdcf_g'))} perpetuity growth or a {mult(g('rdcf_x'))} exit multiple on the same cash flows.",
            f"Enterprise value less net debt, noncontrolling interests and preferred stock ({mmf(-g('net_adj'))} $mm), divided by {g('shares'):,.1f} million shares."], 10)
    # 8 DCF sensitivity
    s = d.slide("Discounted Cash Flow Analysis — Sensitivity", "sensitivity", "Implied value per share at various WACC and terminal value assumptions")
    for k, (key, lab, fx, x) in enumerate([("sens_pgr", "Perpetuity growth rate", pct, Inches(0.5)), ("sens_exit", "Exit multiple (EV / EBITDA)", mult, Inches(6.9))]):
        gr_ = g(key); rows = [["WACC \\ " + lab] + [fx(v) for v in gr_[0][1:]]] + [[pct(r_[0])] + [money(v) for v in r_[1:]] for r_ in gr_[1:]]
        d.table(s, rows, x, Inches(1.6), Inches(5.9), [1.6] + [1] * 5, 10, shade_rows=(3,), rowh=0.4, align_first=PP_ALIGN.CENTER)
    d.notes(s, ["Shaded row is the midpoint WACC; the center cell equals the midpoint value on the prior page. Selected ranges use the midpoint WACC ± one step and the terminal assumption ± one step."], Inches(4.4), 10)
    # 9 LBO
    s = d.slide("Leveraged Buyout Analysis", "lbo", "Illustrative ability of a financial sponsor to pay, based on the illustrative projections")
    rows = [["Key assumptions", ""], ["Total leverage (x LTM EBITDA)", mult(g("lbo_lev"))], ["Blended interest rate", pct(g("lbo_rate"))], ["Exit multiple (EV / EBITDA)", mult(g("lbo_exit"))],
            ["Holding period", f"{g('hold')} years"], ["Fees and expenses", pct(g("lbo_fees")) + " of EV"], ["Target IRR", f"{pct(g('irr_lo'), 0)} – {pct(g('irr_hi'), 0)}"]]
    d.table(s, rows, Inches(0.5), Inches(1.6), Inches(5.6), [3, 2], 11, rowh=0.38)
    rows = [["Results", f"{pct(g('irr_hi'), 0)} IRR", f"{pct(g('irr_lo'), 0)} IRR"], ["Implied EV / LTM EBITDA", mult(g("lbo_mult_b")), mult(g("lbo_mult_a"))],
            ["Implied value per share", money(R["lbo"]["low"]), money(R["lbo"]["high"])], ["Offer price", money(offer), money(offer)]]
    d.table(s, rows, Inches(6.6), Inches(1.6), Inches(6.2), [3, 1.6, 1.6], 11, bold_rows=(2,), shade_rows=(2,), rowh=0.42)
    d.notes(s, ["Debt is assumed outstanding at the opening balance for interest purposes; levered free cash flow repays debt. Sponsor equity at entry is the exit equity value discounted at the target IRR."], Inches(4.6), 10)
    # 10 premiums paid
    s = d.slide("Premiums Paid Analysis", "premiums", "Illustrative range of premiums applied to the unaffected share price")
    d.table(s, [["", "Low", "High"], ["Premium to unaffected price", pct(g("prem_lo"), 0), pct(g("prem_hi"), 0)], ["Unaffected share price", money(g("px_unaff")), money(g("px_unaff"))],
                ["Implied value per share", money(R["premiums"]["low"]), money(R["premiums"]["high"])], ["Offer price premium to unaffected price", pct(g("prem_unaff")), ""]], Inches(0.5), Inches(1.6), Inches(8.0), [3, 1.5, 1.5], 12, bold_rows=(3,), shade_rows=(3,), rowh=0.45)
    d.notes(s, [f"The premium range is an illustrative judgment input ({b['prem']}). A full analysis would apply premiums observed in comparable acquisitions of U.S. public companies."], Inches(4.3), 10)
    # 11 appendix WACC
    s = d.slide("Appendix: Weighted Average Cost of Capital Analysis", "wacc", "Capital asset pricing model with peer betas unlevered and relevered at the target capital structure")
    rows = [["Component", "Value"], ["Risk-free rate", pct(g("rf"), 2)], ["Equity risk premium", pct(g("erp"))], ["Size premium", pct(g("size"))], ["Unlevered beta (peer median)", f"{g('beta_u'):.2f}"],
            ["Target debt / total capitalization", pct(g("dcap"), 0)], ["Relevered beta", f"{g('beta_l'):.2f}"], ["Cost of equity", pct(g("ke"))], ["Pre-tax cost of debt", pct(g("kd"))],
            ["After-tax cost of debt", pct(g("kd_at"))], ["Weighted average cost of capital", pct(g("wacc"))]]
    d.table(s, rows, Inches(0.5), Inches(1.5), Inches(6.0), [3, 1.5], 11, bold_rows=(10,), shade_rows=(10,), rowh=0.36)
    d.text(s, Inches(7.0), Inches(1.5), Inches(5.8), Inches(4), [f"Risk-free rate: {co['market']['risk_free'].get('source', '')}.", f"Betas: {t['price'].get('beta_basis', '')}, unlevered with the Hamada formula at a {pct(g('tax_m'), 0)} marginal tax rate.",
            f"Equity risk premium: {b['erp']}.", f"Cost of debt: {b['kd']}."], 10, False, GREY)
    out = Path(out); out.mkdir(parents=True, exist_ok=True); pp = out / "board_book.pptx"; d.p.save(pp); log(f"wrote {pp} ({d.n} slides)")
    pdf = to_pdf(pp, out, log)
    man = {"schema": SCHEMAS["deck"], "pptx": str(pp), "pdf": str(pdf) if pdf else None, "pages": d.index, "analyses": sorted({x["analysis"] for x in d.index if x["analysis"] and x["analysis"] not in ("summary", "wacc")})}
    save(man, out / "deck.json"); return man

def to_pdf(pptx, out, log=print):
    soffice = shutil.which("soffice") or shutil.which("libreoffice") or ("/Applications/LibreOffice.app/Contents/MacOS/soffice" if Path("/Applications/LibreOffice.app").exists() else None)
    if not soffice: log("LibreOffice not found: board_book.pdf not written; intake can read the .pptx directly"); return None
    prof = Path(tempfile.mkdtemp(prefix="lo_profile_"))
    subprocess.run([soffice, f"-env:UserInstallation=file://{prof}", "--headless", "--convert-to", "pdf", "--outdir", str(out), str(pptx)], capture_output=True, text=True, timeout=240)
    pdf = Path(out) / (Path(pptx).stem + ".pdf"); log(f"wrote {pdf}" if pdf.exists() else "PDF conversion failed"); return pdf if pdf.exists() else None

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("company"); ap.add_argument("terms"); ap.add_argument("valuation"); ap.add_argument("out"); a = ap.parse_args()
    run(a.company, a.terms, a.valuation, a.out)
