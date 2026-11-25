#!/usr/bin/env python3
"""Stage 3 of the ticker-to-proxy lifecycle: the board book, from the recalculated model.

  python3 build_deck.py <company.json> <deal_terms.json> <valuation.json> <out dir> [--house-style auto|default|goldman|...]
      writes board_book.pptx, board_book.pdf, deck.json

Every number on a slide is read from valuation.json, which build_model.py read back from the recalculated workbook, so the
book cannot disagree with the model. Slide titles use the names the board-book classifier (scripts/analyses.py DECK_RX)
recognizes, and the book avoids naming analyses it does not contain (no precedent transactions, no analyst price targets).
The PDF goes through LibreOffice and keeps a text layer, so intake needs no OCR.

House styles. The look of the book (page size, type, palette, title and footer treatment, table and football-field conventions,
cover, contents and divider pages) comes from a profile in references/house-styles/<key>.json. The bank profiles follow the
conventions observed in each bank's publicly filed board presentations (research/ beside them lists the filings). "auto" picks
the profile whose name matches the advisor in deal_terms.json, else the generic default. Every style keeps the ILLUSTRATIVE
stamp and the hypothetical-transaction disclaimer on every page, carries a disclaimer page saying the materials were not
prepared by the advisor, and draws no logo or wordmark."""
import sys, re, json, shutil, subprocess, tempfile, datetime, argparse, copy
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load, save, need, SCHEMAS, disclaimer
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.oxml.ns import qn
from lxml import etree

STYLES = Path(__file__).resolve().parents[2] / "references" / "house-styles"
DW, DH = 13.333, 7.5                       # design space: every position below is in inches on a 13.333 x 7.5 page, scaled to the style's page
RED = "C00000"; WHITE = "FFFFFF"; BLACK = "000000"
ROMAN = ["I", "II", "III", "IV", "V", "VI"]

def styles(): return sorted(p.stem for p in STYLES.glob("*.json"))
def load_style(name="auto", advisor=""):
    """The profile named, or for "auto" the one whose match list names the advisor (else default)."""
    if name in (None, "", "auto"):
        adv = (advisor or "").lower()
        for k in styles():
            st = json.loads((STYLES / f"{k}.json").read_text())
            if any(m in adv for m in st.get("match", [])): return st
        name = "default"
    p = STYLES / f"{name}.json"
    if not p.exists(): raise SystemExit(f"no house style {name!r}; available: auto, {', '.join(styles())}")
    return json.loads(p.read_text())

FMT = {"spaced": False}
def _num(s, unit):
    return f"{s} {unit}" if FMT["spaced"] else f"{s}{unit}"
def money(x, d=2):
    if not isinstance(x, (int, float)): return "NM"
    sp = " " if FMT["spaced"] else ""
    return f"(${sp}{-x:,.{d}f})" if x < 0 else f"${sp}{x:,.{d}f}"
def mmf(x, d=1): return "NM" if not isinstance(x, (int, float)) else (f"({-x:,.{d}f})" if x < 0 else f"{x:,.{d}f}")
def pct(x, d=1):
    if not isinstance(x, (int, float)): return "NM"
    return f"({-x * 100:.{d}f}){' %' if FMT['spaced'] else '%'}" if x < 0 else _num(f"{x * 100:.{d}f}", "%")
def mult(x): return "NM" if not isinstance(x, (int, float)) else _num(f"{x:.1f}", "x")
def rgb(h): return RGBColor.from_string(h)
def sentence(t): return t if not t else t[0].upper() + " ".join(w if (w.isupper() and len(w) > 1) else w.lower() for w in t[1:].split(" "))

class Deck:
    def __init__(self, terms, target, st):
        self.st, self.terms, self.target = st, terms, target
        self.p = Presentation(); self.pw, self.ph = st["page"]["w"], st["page"]["h"]
        self.p.slide_width, self.p.slide_height = Inches(self.pw), Inches(self.ph); self.blank = self.p.slide_layouts[6]
        self.sx, self.sy = self.pw / DW, self.ph / DH; self.fs = min(1.0, self.sx)
        self.n, self.index, self.section = 0, [], None
        self.foot = disclaimer(terms["advisor"], target)
    # geometry in design inches
    def X(self, v): return int(Inches(v * self.sx))
    def Y(self, v): return int(Inches(v * self.sy))
    def text(self, s, x, y, w, h, t, size=12, bold=False, color=None, align=PP_ALIGN.LEFT, italic=False, anchor=MSO_ANCHOR.TOP, font=None, scale=True, rotate=None, underline=False):
        tb = s.shapes.add_textbox(self.X(x), self.Y(y), self.X(w), self.Y(h)); tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
        for i, line in enumerate(t if isinstance(t, list) else [t]):
            para = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); para.alignment = align
            run = para.add_run(); run.text = line; f = run.font; f.size = Pt(size * (self.fs if scale else 1)); f.bold = bold; f.italic = italic; f.underline = underline or None
            f.color.rgb = rgb(color or self.st["text"]["body"]); f.name = font or self.st["font"]["body"]
        if rotate is not None: tb.rotation = rotate
        return tb
    def rect(self, s, x, y, w, h, fill=None, line=None, dash=False, shape=MSO_SHAPE.RECTANGLE, width=0.75):
        r = s.shapes.add_shape(shape, self.X(x), self.Y(y), max(self.X(w), Emu(12000)), max(self.Y(h), Emu(12000)))
        if fill: r.fill.solid(); r.fill.fore_color.rgb = rgb(fill)
        else: r.fill.background()
        if line: r.line.color.rgb = rgb(line); r.line.width = Pt(width); r.line.dash_style = MSO_LINE_DASH_STYLE.DASH if dash else None
        else: r.line.fill.background()
        r.shadow.inherit = False
        style = r._element.find(qn("p:style"))
        if style is not None: r._element.remove(style)   # LibreOffice draws the theme shadow otherwise
        return r
    def line(self, s, x1, y1, x2, y2, color, width=1.0, dash=False):
        ln = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, self.X(x1), self.Y(y1), self.X(x2), self.Y(y2)); ln.line.color.rgb = rgb(color); ln.line.width = Pt(width)
        if dash: ln.line.dash_style = MSO_LINE_DASH_STYLE.DASH
        sp = ln._element.spPr
        if sp.find(qn("a:effectLst")) is None: etree.SubElement(sp, qn("a:effectLst"))   # no theme shadow on rules
        style = ln._element.find(qn("p:style"))
        if style is not None: ln._element.remove(style)   # LibreOffice draws the theme effectRef shadow otherwise
        return ln
    def poly(self, s, pts, fill):
        fb = s.shapes.build_freeform(self.X(pts[0][0]), self.Y(pts[0][1]), scale=1.0)
        fb.add_line_segments([(self.X(a), self.Y(b)) for a, b in pts[1:]], close=True); sh = fb.convert_to_shape()
        sh.fill.solid(); sh.fill.fore_color.rgb = rgb(fill); sh.line.fill.background()
        style = sh._element.find(qn("p:style"))
        if style is not None: sh._element.remove(style)   # no theme shadow
        return sh
    # page furniture
    def furniture(self, s):
        st = self.st; f = st["footer"]
        if f.get("band"): self.rect(s, 0, 6.82, DW, DH - 6.82, f["band"])
        if f.get("rule"): self.line(s, 0.5, 6.84, DW - 0.5, 6.84, f["rule"], 1.5)
        self.text(s, 0.5, 6.86, 11.2, 0.32, self.foot, 7, False, st["text"]["muted"], italic=True)
        num = {"right": str(self.n), "right_bar": f"{self.n} |", "bar_right": f"| {self.n}", "center": str(self.n), "left": str(self.n)}[f["page_number"]]
        al = {"right": PP_ALIGN.RIGHT, "right_bar": PP_ALIGN.RIGHT, "bar_right": PP_ALIGN.RIGHT, "center": PP_ALIGN.CENTER, "left": PP_ALIGN.LEFT}[f["page_number"]]
        px = {"right": 11.8, "right_bar": 11.8, "bar_right": 11.8, "center": 5.9, "left": 0.5}[f["page_number"]]
        self.text(s, px, 7.12, 1.0 if f["page_number"] != "center" else 1.5, 0.3, num, 9, False, st["text"]["muted"], al)
        sub = {"advisor": self.terms["advisor"], "month_year": self.month_year, "section": self.section or "", "codename": self.terms.get("codename") or ""}
        if f.get("left_text") and f["page_number"] != "left": self.text(s, 0.5, 7.12, 5.0, 0.3, f["left_text"].format(**sub), 8, False, st["text"]["muted"])
        if f.get("right_text") and f["page_number"] not in ("right", "right_bar", "bar_right"): self.text(s, 8.8, 7.12, 4.0, 0.3, f["right_text"].format(**sub), 8, True, st["title"]["color"], PP_ALIGN.RIGHT)
        lg = st.get("legend")
        if lg:
            if lg["pos"] == "top_right": self.text(s, 6.3, 0.04, 6.53, 0.3, lg["text"], lg["size"], lg["bold"], lg["color"], PP_ALIGN.RIGHT, lg["italic"])
            else: self.text(s, 3.67, 0.04, 6.0, 0.3, lg["text"], lg["size"], lg["bold"], lg["color"], PP_ALIGN.CENTER, lg["italic"])
        if st["stamp"] == "top_right": box = self.rect(s, 11.3, 0.3, 1.55, 0.42, None, RED, width=1.25); sz = 11
        else: box = self.rect(s, 5.97, 0.03, 1.4, 0.32, None, RED, width=1.0); sz = 8
        tf = box.text_frame; tf.margin_top = tf.margin_bottom = 0; tf.vertical_anchor = MSO_ANCHOR.MIDDLE; tf.word_wrap = False; tf.paragraphs[0].alignment = PP_ALIGN.CENTER; r = tf.paragraphs[0].add_run(); r.text = "ILLUSTRATIVE"
        r.font.size = Pt(sz * self.fs); r.font.bold = True; r.font.color.rgb = rgb(RED); r.font.name = self.st["font"]["body"]
    def slide(self, title, analysis=None, subtitle=None):
        st = self.st; T = st["title"]; s = self.p.slides.add_slide(self.blank); self.n += 1
        shown = sentence(title) if T["case"] == "sentence" else title
        tw = 10.8 if st["stamp"] == "top_right" else 12.3
        if T.get("two_tier") and self.section and self.section != title:                 # the section name as the title, the page name under the rule
            self.text(s, 0.5, 0.3, tw, 0.5, self.section or shown, T["size"], T["bold"], T["color"], font=st["font"]["title"], scale=False)
            self.line(s, 0.5, 0.82, DW - 0.5, 0.82, T["rule_color"], 1.5)
            self.text(s, 0.5, 0.88, 7.0, 0.4, shown, T["size"] * 0.78, True, T.get("subtitle_color", T["color"]), font=st["font"]["title"], scale=False)
            if subtitle: self.text(s, 7.4, 0.92, 5.43, 0.4, subtitle, 10, st["subtitle"]["bold"], st["subtitle"]["color"], PP_ALIGN.RIGHT, st["subtitle"]["italic"])
        else:
            self.text(s, 0.5, 0.3, tw, 0.6, shown, T["size"], T["bold"], T["color"], font=st["font"]["title"], scale=False)   # the title is the page's first text line
            if subtitle: self.text(s, 0.5, 0.85, 12.3, 0.4, subtitle, 12, st["subtitle"]["bold"], st["subtitle"]["color"], italic=st["subtitle"]["italic"])
            if T["rule"] == "under": self.line(s, 0.5, 1.27, DW - 0.5, 1.27, T["rule_color"], T.get("rule_width", 1.75))
            elif T["rule"] == "above_short": self.rect(s, 0.5, 0.2, 1.4, 0.07, T["rule_color"])
        self.furniture(s)
        self.index.append({"page": self.n, "title": title, "analysis": analysis}); return s
    def table(self, s, rows, x, y, w, colw=None, size=10, head=1, bold_rows=(), shade_rows=(), rowh=0.28, align_first=PP_ALIGN.LEFT):
        st = self.st["table"]; nr, nc = len(rows), len(rows[0]); rowh *= st.get("density", 1.0); size *= st.get("font_scale", 1.0); txt_head = st["header"] == "text"
        hcol = st.get("header_text_color") or st["header_fill"]; hrule = st.get("header_rule", st["header_fill"])   # text headers: label color, rule under them (None = no rule)
        gf = s.shapes.add_table(nr, nc, self.X(x), self.Y(y), self.X(w), self.Y(rowh * nr)); tb = gf.table; tb.horz_banding = False; tb.first_row = False
        W_ = self.X(w)
        if colw:
            tot = sum(colw)
            for i, cw in enumerate(colw): tb.columns[i].width = int(W_ * cw / tot)
        for i, row in enumerate(rows):
            tb.rows[i].height = self.Y(rowh)
            for j, v in enumerate(row):
                c = tb.cell(i, j); c.text = " " if v is None or str(v) == "" else str(v)   # a run in every cell, so an empty cell takes the table's type size
                c.margin_left = c.margin_right = Inches(0.05); c.margin_top = c.margin_bottom = Inches(0.02); c.vertical_anchor = MSO_ANCHOR.MIDDLE
                para = c.text_frame.paragraphs[0]; para.alignment = align_first if j == 0 else PP_ALIGN.CENTER
                for run in para.runs:
                    run.font.size = Pt(size * self.fs); run.font.name = self.st["font"]["body"]; run.font.bold = i < head or i in bold_rows
                    run.font.color.rgb = rgb((hcol if txt_head else st["header_text"]) if i < head else self.st["text"]["table"])
                    if i < head and txt_head and st.get("header_underline") and run.text.strip(): run.font.underline = True
                c.fill.solid(); c.fill.fore_color.rgb = rgb((WHITE if txt_head else st["header_fill"]) if i < head else (st["stat_fill"] if i in shade_rows else WHITE))
                top = hrule if (txt_head and i == head and hrule) else None   # the header rule also as the first body row's top edge, which LibreOffice draws
                if i < head and txt_head:
                    if hrule: self.border(c, hrule, 12700)
                elif i >= head and (st.get("rule_color") or top): self.border(c, st.get("rule_color"), top=top)
        return tb
    def border(self, cell, color, w=6350, top=None):
        tcPr = cell._tc.get_or_add_tcPr()
        for side in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
            col = color if side == "a:lnB" else (top if side == "a:lnT" else None)
            ln = etree.SubElement(tcPr, qn(side), w=str((12700 if side == "a:lnT" else w) if col else 0))
            if col: sf = etree.SubElement(ln, qn("a:solidFill")); etree.SubElement(sf, qn("a:srgbClr"), val=col)
            else: etree.SubElement(ln, qn("a:noFill"))
            tcPr.remove(ln); tcPr.insert(["a:lnL", "a:lnR", "a:lnT", "a:lnB"].index(side), ln)
    def notes(self, s, lines, y=5.9, size=9):
        return self.text(s, 0.5, y, 12.3, 0.9, lines, size, False, self.st["text"]["muted"], italic=self.st["text"]["notes_italic"])
    # cover, disclaimer, contents and dividers
    def cover(self, date, t):
        st = self.st; cv = st["cover"]; s = self.p.slides.add_slide(self.blank); self.n += 1; self.index.append({"page": 1, "title": "Cover", "analysis": None})
        code = self.terms.get("codename") or "Project"; co_line = cv.get("company_line", True)
        sub = ["Discussion Materials"] + ([f"Prepared for {self.terms['addressee']} of {t['name']}"] if co_line else [])
        style = cv["style"]
        if style == "band":
            self.rect(s, 0, 0, DW, 4.2, cv["color"])
            self.text(s, 0.8, 1.2, 11.5, 0.8, code, 36, True, cv["title_color"], scale=False); self.text(s, 0.8, 2.1, 11.5, 1.2, sub, 20, False, WHITE, scale=False)
            self.text(s, 0.8, 4.6, 11.5, 0.5, date, 16, False, cv["accent"], scale=False)
        elif style == "wedge":
            self.poly(s, [(9.3, 0), (DW, 0), (DW, DH), (11.4, DH)], cv["accent"])
            if cv.get("second_wedge", True): self.poly(s, [(12.1, DH), (DW, 3.6), (DW, DH)], cv["color"])
            by = cv.get("block_y", 2.5); ts = cv.get("title_size", 28); th = ts / 72 * 1.25
            self.text(s, 0.8, by, 8.2, th + 0.1, code, ts, cv.get("title_bold", False), cv["title_color"], scale=False)
            self.text(s, 0.8, by + th + 0.05, 8.2, 0.5, sub[0], ts * 0.75, False, cv["title_color"], italic=cv.get("subtitle_italic", False), scale=False)
            ry = by + th + 0.05 + ts * 0.75 / 72 * 1.25 + 0.2
            self.line(s, 0.8, ry, 8.6, ry, cv["title_color"], 1.0); self.text(s, 0.8, ry + 0.1, 8.2, 0.9, sub[1:] + [date], 14, False, BLACK, scale=False)
        elif style == "rules":
            rx0, rx1 = (0, DW) if cv.get("full_bleed") else (0.5, DW - 0.5)
            self.line(s, rx0, 2.5, rx1, 2.5, cv["color"], 1.0); self.line(s, rx0, 4.0, rx1, 4.0, cv["color"], 1.0)
            self.text(s, 0.5, 2.7, 12.3, 0.6, f"Project {code}" if not code.lower().startswith("project") else code, 22, True, cv["title_color"], scale=False)
            self.text(s, 0.5, 3.3, 12.3, 0.6, sub, 13, False, BLACK, scale=False); self.text(s, 0.5, 4.1, 12.3, 0.4, f"{date}  /  Confidential", 11, False, "808080", scale=False)
        elif style == "frame":
            self.rect(s, 0.25, 0.25, DW - 0.5, (DH - 0.5) if cv.get("frame_full") else 5.6, None, cv["color"], shape=MSO_SHAPE.ROUNDED_RECTANGLE, width=1.25).adjustments[0] = 0.03
            self.text(s, 0.8, 2.3, 11.5, 0.9, code, cv.get("title_size", 40), cv.get("title_bold", False), cv["title_color"], scale=False); self.text(s, 0.8, 3.3, 11.5, 1.0, sub, 18, False, BLACK, scale=False)
            self.text(s, 6.3, 5.25, 6.4, 0.4, f"{date} | Strictly Private and Confidential", 11, False, BLACK, PP_ALIGN.RIGHT, scale=False)
        elif style == "plain_bottom_rule":
            self.text(s, 0.8, 2.0, 11.5, 0.9, code, 40, cv.get("title_bold", False), cv["title_color"], scale=False)
            self.text(s, 0.8, 3.0, 11.5, 1.2, [f"Presentation to {self.terms['addressee']}" if self.terms['addressee'].lower().startswith('the ') else f"Presentation to the {self.terms['addressee']}"] + ([t["name"]] if co_line else []), 24, False, cv["title_color"], scale=False)
            self.text(s, 0.8, 4.3, 11.5, 0.5, date, 16, False, cv["title_color"], scale=False)
            self.rect(s, 0 if cv.get("full_bleed") else 0.5, 5.55, DW if cv.get("full_bleed") else DW - 1.0, 0.06, cv["accent"]); self.text(s, 0.5, 5.65, 8, 0.3, "S T R I C T L Y   P R I V A T E   A N D   C O N F I D E N T I A L", 8, False, "5D5F62", scale=False)
        elif style == "plain_sub_first":      # "Presentation to ..." large first, the project name under it in the accent color
            self.text(s, 0.8, 1.9, 11.5, 1.1, [f"Presentation to {self.terms['addressee']}" if self.terms['addressee'].lower().startswith('the ') else f"Presentation to the {self.terms['addressee']}"], 30, False, BLACK, scale=False)
            self.text(s, 0.8, 3.0, 11.5, 0.6, code, 24, False, cv["title_color"], scale=False)
            if co_line: self.text(s, 0.8, 3.6, 11.5, 0.5, t["name"], 16, False, BLACK, scale=False)
            ay = 4.3 if co_line else 3.75
            self.text(s, 0.8, ay, 11.5, 0.5, self.terms["advisor"], 15, True, BLACK, scale=False); self.text(s, 0.8, ay + 0.45, 11.5, 0.5, date, 14, False, BLACK, scale=False)
            self.line(s, 0.5, 5.85, DW - 0.5, 5.85, cv["accent"], 0.75)
        else:   # plain
            ts = cv.get("title_size", 34); self.text(s, 0.8, 2.2, 11.5, 0.9, code, ts, cv.get("title_bold", False), cv["title_color"], scale=False)
            ry = 2.2 + 0.15 + ts / 72 * 1.25 if cv.get("rule_under_title") else 3.15
            self.line(s, 0.8, ry, (DW - 0.5) if cv.get("rule_under_title") else 9.0, ry, cv["accent"], 1.0)
            self.text(s, 0.8, ry + 0.1, 11.5, 1.0, sub, cv.get("sub_size", 20), cv.get("title_bold", False), BLACK if cv["title_color"] in ("7399C6",) else cv["title_color"], scale=False)
            self.text(s, 0.8, ry + 0.1 + len(sub) * cv.get("sub_size", 20) / 72 * 1.3 + 0.3, 11.5, 0.5, date, 15, cv.get("title_bold", False), cv["title_color"] if cv["title_color"] not in ("7399C6",) else BLACK, scale=False)
        cw = 8.3 if style == "wedge" else 11.5
        self.text(s, 0.8, 6.05 if style not in ("band",) else 5.2, cw, 0.4, f"Illustrative materials in the form a financial advisor ({self.terms['advisor']}) would present", 11, False, "808080", italic=True, scale=False)
        self.text(s, 0.8, 6.45, cw, 0.8, self.foot, 9, True, RED, scale=False)
        return s
    def disclaimer_page(self):
        s = self.slide("Disclaimer"); adv = self.terms["advisor"]
        paras = [self.foot,
                 "These materials are a demonstration generated by software from public SEC filings and market data for a hypothetical transaction. The projections are illustrative and derived from reported history; they are not management projections. Nothing in these materials is investment advice, a recommendation or an opinion as to fairness."]
        if self.st["key"] != "default":
            paras.append(f"The layout, typefaces and colors follow conventions observed in presentations that {adv} has filed publicly with the SEC as exhibits to transaction statements. "
                         f"These materials were not prepared, reviewed or approved by {adv}, and no affiliation with or endorsement by {adv} is implied. No logo, trademark or proprietary typeface of {adv} is reproduced.")
        self.text(s, 0.5, 1.6, 12.3, 4.8, [x for p_ in paras for x in (p_, "")][:-1], 11, False, self.st["text"]["body"])
        return s
    def toc_list(self, s, starts, names):
        """A plain contents list, as filed decks set it: numeral, section name, page number (optional), a hairline under each row."""
        o = self.st.get("toc_opts") or {}; col = o.get("color", self.st["title"]["color"]); y = 1.9; rule = o.get("rule_color", "BFBFBF")
        sz = o.get("size", 14); pitch = o.get("row_pitch", 0.62); x0 = 0.5 + o.get("indent", 0.8); nb = o.get("numbering", "roman")
        flip = o.get("layout") == "name_then_numeral"; pages = o.get("pages", True) and not flip; mw = 0.0 if (nb == "none" or flip) else 0.8
        ncol, nbold = o.get("name_color", self.st["text"]["body"]), o.get("bold", False); hc = self.st["text"]["muted"]
        if pages: self.text(s, 10.6, y - 0.4, 1.4, 0.3, "Page", 10, True, hc, PP_ALIGN.RIGHT)
        if flip: self.text(s, 10.6, y - 0.4, 1.4, 0.3, "Section", 10, True, hc, PP_ALIGN.RIGHT)
        num = 0
        for (lab, p), name in zip(starts, names):
            appendix = name == "Appendix"; mark = "" if appendix or nb == "none" else (ROMAN[num] if nb == "roman" else str(num + 1)) + o.get("numeral_suffix", "")
            if appendix and o.get("appendix_label"): name = o["appendix_label"]
            if not appendix: num += 1
            if mw: self.text(s, x0, y, mw, pitch, mark, sz, nbold, col)
            self.text(s, x0 + mw, y, 8.4, pitch, name, sz, nbold, ncol)
            if flip: self.text(s, 10.6, y, 1.4, pitch, mark, sz, nbold, col, PP_ALIGN.RIGHT)
            if pages: self.text(s, 10.6, y, 1.4, pitch, str(p), sz, False, self.st["text"]["body"], PP_ALIGN.RIGHT)
            if rule: self.line(s, x0, y + pitch * 0.78, 12.0, y + pitch * 0.78, rule, 0.5)
            y += pitch
    def divider(self, label):
        dv = self.st["dividers"]; s = self.p.slides.add_slide(self.blank); self.n += 1; st = dv["style"]; col = dv.get("color", BLACK)
        dx, dy = dv.get("x", 0.8), dv.get("y", 3.2)
        if st == "rules":
            rx0, rx1 = (0, DW) if dv.get("full_bleed") else (0.5, DW - 0.5)
            self.line(s, rx0, 2.55, rx1, 2.55, dv.get("rule_color", "B0B0B0"), 1.0); self.line(s, rx0, 3.95, rx1, 3.95, dv.get("rule_color", "B0B0B0"), 1.0)
            self.text(s, 0.5, 2.95, 12.3, 0.6, label, dv["size"], True, col, scale=False)
        elif st == "appendix_only":
            cv = self.st["cover"]; self.poly(s, [(9.3, 0), (DW, 0), (DW, DH), (11.4, DH)], cv["accent"]); self.poly(s, [(12.1, DH), (DW, 3.6), (DW, DH)], cv["color"])
            self.text(s, dx, dy + 0.1, 8.0, 0.7, label, dv["size"], False, col, scale=False)
        else:
            self.text(s, dx, dy, 11.5, 0.8, label, dv["size"], st in ("roman",), col, scale=False)
            if dv.get("rule"): self.line(s, dx, dy + 0.75, (DW - 0.5) if dv.get("rule_full") else 9.0, dy + 0.75, dv.get("rule_color", col), 1.0)
        self.furniture(s); self.index.append({"page": self.n, "title": label, "analysis": None}); return s

def build_pages(d, co, terms, val, date):
    t = co["target"]; C = val["cells"]; g = lambda k: C[k]["value"]; R = val["ranges"]; st = d.st; ff = st["ff"]
    offer = g("s_offer"); b = val["assumption_basis"]
    yrs = g("dcf_years")[0]; ylab = [f"{int(yrs[0])}A"] + [f"{int(y)}E" for y in yrs[1:]]
    rv, eb, uf = g("row_rev")[0], g("row_ebitda")[0], g("row_ufcf")[0]; gr, mg = g("row_g")[0], g("row_m")[0]

    def p_overview():
        s = d.slide("Transaction Overview", None, f"Hypothetical acquisition of {t['name']} by {terms['buyer']}")
        rows = [["Proposed transaction", ""], ["Offer price per share", money(offer)], ["Consideration", terms["consideration"].capitalize()],
                ["Premium to unaffected price " + f"({money(g('px_unaff'))} on {terms['unaffected_date']})", pct(g("prem_unaff"))],
                ["Premium to 30-trading-day average", pct(g("prem_30d"))], ["Premium (discount) to 52-week high", pct(g("prem_hi52"))],
                ["Implied equity value ($mm)", mmf(g("offer_equity"))], ["Implied enterprise value ($mm)", mmf(g("offer_ev"))],
                ["Implied EV / LTM revenue", mult(g("offer_ev_rev"))], ["Implied EV / LTM EBITDA", mult(g("offer_ev_ebitda"))], ["Implied EV / next fiscal year EBITDA (illustrative projections)", mult(g("offer_ev_fy1"))]]
        d.table(s, rows, 0.5, 1.6, 8.2, [5, 2], 12, rowh=0.36)
        d.text(s, 9.1, 1.6, 3.8, 3.5, [f"Buyer: {terms['buyer']} ({terms['buyer_type']})", f"Transaction type: {'Rule 13e-3 going-private' if terms['regime'] == '13e-3' else 'third-party acquisition'}",
                f"Shares outstanding: {g('shares'):,.1f} million", f"Valuation date: {date}", f"Market data as of {co['as_of']}"], 11)
        d.notes(s, ["Implied enterprise value equals implied equity value plus total debt, noncontrolling interests and preferred stock, less cash and short-term investments, from the latest balance sheet filed with the SEC.",
                    "LTM figures from SEC XBRL filings. Projections are illustrative, derived from reported history (see the valuation model, Assumptions tab); they are not management projections."])

    def p_summary():
        s = d.slide("Summary of Financial Analyses", "summary", "Implied value per share of common stock")
        core = [("Discounted Cash Flow Analysis — perpetuity growth", "dcf_pgr", f"WACC {pct(g('wacc') - g('wacc_step'))}–{pct(g('wacc') + g('wacc_step'))}; perpetuity growth {pct(g('g_mid') - g('g_step'))}–{pct(g('g_mid') + g('g_step'))}"),
                ("Discounted Cash Flow Analysis — exit multiple", "dcf_exit", f"WACC {pct(g('wacc') - g('wacc_step'))}–{pct(g('wacc') + g('wacc_step'))}; exit multiples {mult(g('exit_mid') - g('exit_step'))}–{mult(g('exit_mid') + g('exit_step'))} EBITDA"),
                ("Selected Public Companies Analysis", "comps", f"{mult(g('comps_lo'))}–{mult(g('comps_hi'))} EV / LTM EBITDA"),
                ("Leveraged Buyout Analysis", "lbo", f"{pct(g('irr_lo'), 0)}–{pct(g('irr_hi'), 0)} target IRR; {mult(g('lbo_lev'))} leverage; {mult(g('lbo_exit'))} exit"),
                ("Premiums Paid Analysis (illustrative)", "premiums", f"{pct(g('prem_lo'), 0)}–{pct(g('prem_hi'), 0)} premium to unaffected price")]
        ref = [("52-Week Trading Range (for reference only)", "trading_range", "52-week low and high closing prices")]
        tiers = ff.get("label_tiers", 1) == 2
        if tiers:                               # two-tier labels: a method group on the left, the specific analysis beside it
            short = {"dcf_pgr": "Perpetuity growth", "dcf_exit": "Exit multiple", "comps": "Selected public companies", "lbo": "Illustrative LBO",
                     "premiums": "Premiums paid (illustrative)", "trading_range": "52-week trading range"}
            grp = {"dcf_pgr": "Discounted Cash Flow", "dcf_exit": "Discounted Cash Flow", "comps": "Trading Multiples", "lbo": "Ability to Pay",
                   "premiums": "Premiums Paid", "trading_range": "For Reference Only"}
            core = [(short[k], k, bs) for _, k, bs in core]; ref = [(short[k], k, bs) for _, k, bs in ref]
        groups = [(ref, True), (core, False)] if ff["reference_position"] == "top" else [(core, False), (ref, True)]
        items = [(it, isref) for grp_, isref in groups for it in grp_]
        lines = [offer] + ([g("px_unaff")] if ff.get("unaffected_color") else [])
        lo_all = min(min(R[k]["low"], R[k]["high"]) for (_, k, _), _r in items); hi_all = max(max(R[k]["low"], R[k]["high"]) for (_, k, _), _r in items)
        lo_ax = max(0, (min([lo_all] + lines) * 0.85) // 5 * 5); hi_ax = (max([hi_all] + lines) * 1.1 // 5 + 1) * 5
        right = ff["basis"] == "right" or ff["label_blocks"]          # label blocks leave no room for basis text beside them
        mid = right and ff.get("description_position") == "middle"; mh = ff.get("multiples")
        GX, GW = (0.5, 1.35) if tiers else (0.5, 0)
        LX = GX + GW + (0.08 if tiers else 0); LW = (2.1 if tiers else (3.0 if mid else 3.3)) if right else 4.7
        RE = DW - 0.5; MW = 1.45 if mh else 0; MX = RE - MW
        if not right: DX, DWD, X0, X1 = None, 0, 5.3, MX - 0.4
        elif mid: DX = LX + LW + 0.12; DWD = 2.55; X0 = DX + DWD + 0.95; X1 = MX - 0.95
        else: DWD = 3.1; DX = MX - DWD - (0.1 if mh else 0); X0 = LX + LW + 0.9; X1 = DX - 0.3
        top_lab = ff["offer_label"] in ("above", "box_top"); hdrs = ff.get("headers"); rot = ff.get("reference_label_rotated")
        reflab = None if (tiers or rot) else ff.get("reference_label")
        Y0 = (2.05 if top_lab else 1.6) + (0.3 if hdrs else 0); rowh = ff.get("row_height") or (0.6 if top_lab else 0.56); gap = 0.28 if (ff.get("reference_label") and ff.get("separator", True)) else 0
        xp = lambda v: X0 + (X1 - X0) * (v - lo_ax) / (hi_ax - lo_ax)
        wd = (lambda v: money(v, 0)) if ff.get("whole_dollars") else money
        vcol = ff.get("value_color", BLACK); lsz = ff.get("label_size", 10 if ff["label_blocks"] else 11)
        net = g("offer_ev") - g("offer_equity"); ltm = g("h_ebitda_ltm")
        imult = lambda v: (v * g("shares") + net) / ltm if ltm else None
        if hdrs:                                # column headers over the label, description, chart and multiples areas, with a rule under them
            hy = Y0 - (0.95 if top_lab else 0.4); hc = st["title"]["color"]
            d.text(s, GX, hy, LW + GW, 0.3, hdrs[0], 9, True, hc); d.text(s, X0, hy, X1 - X0, 0.3, hdrs[1], 9, True, hc, PP_ALIGN.CENTER)
            if right and len(hdrs) > 2: d.text(s, DX, hy, DWD, 0.3, hdrs[2], 9, True, hc)
            if mh: d.text(s, MX, hy - 0.12, MW, 0.42, mh, 8, True, hc, PP_ALIGN.CENTER)
            d.line(s, GX, hy + 0.3, RE, hy + 0.3, hc, 0.75)
        elif right: d.text(s, DX, Y0 - 0.32, DWD, 0.3, "Methodology / assumptions", 9, True, st["text"]["muted"])
        y = Y0; prev_ref = None; ybot = y; spans = {}; refspan = []; vlabels = []
        for n_, ((label, k, basis), isref) in enumerate(items):
            if prev_ref is not None and isref != prev_ref and gap and ff.get("separator", True):
                d.line(s, 0.5, y + gap / 2, DW - 0.5, y + gap / 2, "A0A0A0", 0.75, dash=True); y += gap
            if isref and reflab and prev_ref is not True:
                d.text(s, LX, y - (0.02 if prev_ref is None else 0.04), 4.0, 0.25, reflab, 8, True, st["text"]["muted"], italic=True); y += 0.22
            prev_ref = isref
            if tiers: spans.setdefault(grp[k], [y, y]); spans[grp[k]][1] = y + rowh
            if isref: refspan = [refspan[0] if refspan else y, y + rowh]
            lo, hi = R[k]["low"], R[k]["high"]
            color = ff["reference"] if isref else ((ff.get("method_colors") or {}).get(k) or ff["core"])
            tx = LX + (0.38 if ff.get("numbered") else 0.05)
            if ff["label_blocks"]:
                lf = (ff.get("label_fills") or {}).get(k) or color
                d.rect(s, LX, y + 0.03, LW, rowh - 0.06, lf); d.text(s, tx, y + 0.03, LX + LW - tx - 0.05, rowh - 0.06, label, lsz, True, WHITE, anchor=MSO_ANCHOR.MIDDLE)
                if not right: d.text(s, LX + LW + 0.05, y + 0.3, X0 - LX - LW - 0.6, 0.3, basis, 8, False, st["text"]["muted"], italic=True)
            else:
                d.text(s, tx - 0.05, y, LX + LW - tx + 0.05, rowh, label, lsz, True, anchor=MSO_ANCHOR.MIDDLE)
                if not right: d.text(s, LX, y + 0.28, LW, 0.35, basis, 8, False, st["text"]["muted"], italic=True)
            if ff.get("numbered"):
                c_ = d.rect(s, LX + 0.07, y + rowh / 2 - 0.13, 0.26, 0.26, WHITE if ff["label_blocks"] else color, None, shape=MSO_SHAPE.OVAL)
                d.text(s, LX + 0.02, y + rowh / 2 - 0.15, 0.36, 0.3, str(n_ + 1), 8, True, color if ff["label_blocks"] else WHITE, PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            if right: d.text(s, DX, y, DWD, rowh, ("" if mid else "■ ") + basis, 8, False, st["text"]["body"], anchor=MSO_ANCHOR.MIDDLE)
            bh = min(rowh - 0.12, 0.3); by = y + (rowh - bh) / 2
            d.rect(s, xp(lo), by, max(xp(hi) - xp(lo), 0.02), bh, color)
            vlabels += [(xp(lo), y, wd(lo), True), (xp(hi), y, wd(hi), False)]
            if mh: d.text(s, MX, y, MW, rowh, f"{mult(imult(lo))} – {mult(imult(hi))}", 9, False, st["text"]["body"], PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            if ff.get("row_rules"): d.line(s, GX, y + rowh, RE, y + rowh, ff["row_rules"], 0.5)
            y += rowh; ybot = y
        for gname, (y0_, y1_) in spans.items():   # group cells of the two-tier labels
            d.text(s, GX, y0_, GW, y1_ - y0_, gname, 9, True, st["title"]["color"], anchor=MSO_ANCHOR.MIDDLE)
            d.line(s, GX, y1_, LX + LW, y1_, "BFBFBF", 0.5)
        if rot and refspan and ff.get("reference_label"):   # reference label set vertically beside the reference rows
            h_ = refspan[1] - refspan[0]; w_ = max(h_, 2.2)
            d.text(s, 0.27 - w_ / 2, (refspan[0] + refspan[1]) / 2 - 0.12, w_, 0.24, ff["reference_label"], 7, True, st["text"]["muted"], PP_ALIGN.CENTER, italic=True, rotate=270)
        if ff.get("axis"):                      # value axis with light gridlines
            step = next(x for x in (5, 10, 20, 25, 50, 100, 200, 250, 500) if (hi_ax - lo_ax) / x <= 8); v = -(-lo_ax // step) * step
            while v <= hi_ax:
                d.line(s, xp(v), Y0 - 0.05, xp(v), ybot, "D9D9D9", 0.5); d.text(s, xp(v) - 0.4, ybot + 0.02, 0.8, 0.22, money(v, 0), 8, False, st["text"]["muted"], PP_ALIGN.CENTER); v += step
            ybot += 0.22
        marks = [("Offer price", offer, ff["offer_color"], ff["offer_dash"])]
        if ff.get("unaffected_color"): marks.insert(0, (ff.get("unaffected_label", "Unaffected price") + f" ({terms['unaffected_date']})", g("px_unaff"), ff["unaffected_color"], True))
        pit = ff.get("price_label_italic", False)
        for i, (lab, v, colr, dash) in enumerate(marks):
            d.line(s, xp(v), Y0 - 0.1, xp(v), ybot - (0.22 if ff.get("axis") else 0), colr, 2.0 if not dash else 1.75, dash)
            txt = f"{lab}: {money(v)}"
            if ff["offer_label"] == "below": d.text(s, xp(v) - 1.6, ybot + 0.02 + 0.25 * i, 3.2, 0.3, txt, 10, True, colr, PP_ALIGN.CENTER, pit)
            elif ff["offer_label"] == "box_top":
                bx = d.rect(s, xp(v) - 1.3, Y0 - 0.48 - 0.36 * i, 2.6, 0.32, WHITE, BLACK, width=0.75); d.text(s, xp(v) - 1.3, Y0 - 0.48 - 0.36 * i, 2.6, 0.32, txt, 9, True, BLACK, PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            else: d.text(s, xp(v) - 1.6, Y0 - 0.62 + 0.24 * i, 3.2, 0.28, txt, 10, True, colr, PP_ALIGN.CENTER, pit)
        for x_, y_, txt, left in vlabels:      # value labels last, on white, so a price line passes behind them
            w_ = 0.075 * len(txt) + 0.1; bh_ = min(rowh, 0.24)
            tb = d.text(s, x_ - w_ - 0.04 if left else x_ + 0.04, y_ + (rowh - bh_) / 2, w_, bh_, txt, 10, ff["value_bold"], vcol, PP_ALIGN.RIGHT if left else PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE)
            tf = tb.text_frame; tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0; tf.word_wrap = False; tb.fill.solid(); tb.fill.fore_color.rgb = rgb(WHITE)
        d.notes(s, ["The 52-week trading range is presented for reference only and is not a valuation methodology. Premiums paid range is illustrative.",
                    "Implied values per share are rounded to the nearest $0.01 and are based on the illustrative projections and the assumptions in the valuation model."], 6.25)

    def p_trading():
        s = d.slide("52-Week Trading Range", "trading_range", f"{t['name']} daily closing share price, 52 weeks to {t['price']['date']} (for reference only)")
        hist = t["price"]["history_1y"]
        if hist:
            cd = CategoryChartData(); step = max(1, len(hist) // 120); pts = hist[::step]
            cd.categories = [datetime.date.fromisoformat(x[0]).strftime("%b %y") for x in pts]; cd.add_series("Closing price", [x[1] for x in pts])
            cd.add_series("Offer price", [offer] * len(pts))
            ch = s.shapes.add_chart(XL_CHART_TYPE.LINE, d.X(0.5), d.Y(1.5), d.X(8.6), d.Y(4.3), cd).chart
            ch.has_legend = True; ch.legend.position = XL_LEGEND_POSITION.BOTTOM; ch.legend.include_in_layout = False
            ch.series[0].format.line.color.rgb = rgb(st["chart"]["primary"]); ch.series[1].format.line.color.rgb = rgb(st["chart"]["offer"]); ch.series[0].smooth = False
            ch.series[1].format.line.dash_style = MSO_LINE_DASH_STYLE.DASH
            ch.value_axis.tick_labels.font.size = Pt(9 * d.fs); ch.category_axis.tick_labels.font.size = Pt(8 * d.fs); ch.value_axis.has_major_gridlines = False
            ch.value_axis.tick_labels.number_format = '"$"#,##0'; ch.value_axis.tick_labels.number_format_is_linked = False
        d.table(s, [["Share price statistics", ""], ["52-week high", money(g("px_hi"))], ["52-week low", money(g("px_lo"))], ["30-trading-day average", money(g("px_30d"))],
                    ["Unaffected price", money(g("px_unaff"))], ["Offer price", money(offer)], ["Offer premium to 52-week high", pct(g("prem_hi52"))]], 9.4, 1.6, 3.4, [3, 2], 11, rowh=0.38)
        d.notes(s, [f"Source: daily closing prices ({t['price']['source']}). Presented for reference only."])

    def p_projections():
        s = d.slide("Illustrative Financial Projections", None, "($ in millions) — derived from reported history; not management projections")
        rows = [["Fiscal year"] + ylab, ["Revenue"] + [mmf(x) for x in rv], ["  % growth", ""] + [pct(x) for x in gr[1:]], ["EBITDA"] + [mmf(x) for x in eb], ["  % margin", ""] + [pct(x) for x in mg[1:]],
                ["Unlevered free cash flow", ""] + [mmf(x) for x in uf[1:]]]
        d.table(s, rows, 0.5, 1.6, 12.3, [3] + [1] * len(ylab), 11, bold_rows=(1, 3, 5), rowh=0.38)
        d.notes(s, [f"Revenue growth: {b['growth']}.", f"EBITDA margin: {b['margin']}; D&A: {b['da']}; capital expenditures: {b['capex']}; net working capital: {b['nwc']}.",
                    "Unlevered free cash flow = EBIT less taxes at 25%, plus D&A, less capital expenditures and the increase in net working capital. Stock-based compensation is treated as a cash expense (not added back)."], 4.4, 10)

    def p_comps():
        s = d.slide("Selected Public Companies Analysis", "comps", f"Peers: {co['peer_basis']}")
        cs = st.get("comps") or {}; tr = g("comps_target_row")[0]; peers = g("comps_table")
        names = {"max": "Maximum", "75th": "75th percentile", "median": "Median", "mean": "Mean", "25th": "25th percentile", "min": "Minimum"}
        labels = ["Maximum", "75th percentile", "Median", "Mean", "25th percentile", "Minimum"]; stats = dict(zip(labels, g("comps_stats")))
        want = [names[x] for x in cs.get("stats", ["75th", "median", "25th"])]
        if cs.get("style") == "bars":           # peers charted by EV / LTM EBITDA, with the median and the Company beside them
            pts = sorted([(r_[0], r_[14]) for r_ in peers if isinstance(r_[14], (int, float))], key=lambda x: -x[1])
            med = stats["Median"][14]; sv = tr[14] if isinstance(tr[14], (int, float)) else 0; first = cs.get("subject_first")
            sl = f"{t['name']} (Unaffected)"; cats = ([sl] if first else []) + [n for n, _ in pts] + ["Median"] + ([] if first else [sl])
            vals = ([sv] if first else []) + [v for _, v in pts] + [med] + ([] if first else [sv])
            cd = CategoryChartData(); cd.categories = cats; cd.add_series("EV / LTM EBITDA", vals)
            gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, d.X(0.5), d.Y(1.75), d.X(8.8), d.Y(3.9), cd); ch = gf.chart
            d.text(s, 0.5, 1.45, 8.8, 0.3, "EV / LTM EBITDA", 11, True, st["title"]["color"])
            ch.has_title = False; ch.has_legend = False; ch.value_axis.visible = False; ch.value_axis.has_major_gridlines = False
            ch.category_axis.tick_labels.font.size = Pt(7 * d.fs); ch.category_axis.format.line.color.rgb = rgb("BFBFBF")
            pl = ch.plots[0]; pl.gap_width = 60; pl.has_data_labels = True; dl = pl.data_labels; dl.number_format = '0.0"x"'; dl.number_format_is_linked = False
            dl.font.size = Pt(9 * d.fs); dl.position = XL_LABEL_POSITION.OUTSIDE_END
            ser = pl.series[0]; prim = cs.get("bar_color") or st["chart"]["primary"]
            for i_ in range(len(cats)):
                kind = "subject" if (i_ == 0 if first else i_ == len(cats) - 1) else ("median" if cats[i_] == "Median" else "peer")
                pt = ser.points[i_]; pt.format.fill.solid(); pt.format.fill.fore_color.rgb = rgb({"peer": prim, "median": "A6A6A6", "subject": cs.get("subject_color") or st["chart"]["offer"]}[kind])
        else:
            hdr = ["Company", "Enterprise value ($mm)", "EV / LTM revenue", "EV / LTM EBITDA", "EV / LTM EBIT", "LTM EBITDA margin"]
            subj = [f"{t['name']} (at unaffected price)", mmf(tr[8], 0), mult(tr[13]), mult(tr[14]), mult(tr[15]), pct(tr[16])]
            top = cs.get("subject_position") == "top"
            rows = [hdr] + ([subj] if top else []) + [[r_[0], mmf(r_[8], 0), mult(r_[13]), mult(r_[14]), mult(r_[15]), pct(r_[16])] for r_ in peers]
            base = len(rows); rows += [[lab, "", mult(stats[lab][13]), mult(stats[lab][14]), mult(stats[lab][15]), pct(stats[lab][16])] for lab in want]
            if not top: rows += [subj]
            sr = tuple(range(base, base + len(want)))
            d.table(s, rows, 0.5, 1.5, 8.8, [4, 1.6, 1.3, 1.3, 1.3, 1.3], 9, bold_rows=sr + ((1,) if top else ()), shade_rows=sr, rowh=0.3)
        d.table(s, [["Implied value per share", ""], ["Selected EV / LTM EBITDA", f"{mult(g('comps_lo'))} – {mult(g('comps_hi'))}"], [f"{t['ticker']} LTM EBITDA ($mm)", mmf(g("h_ebitda_ltm"))],
                    ["Implied value per share", f"{money(R['comps']['low'])} – {money(R['comps']['high'])}"], ["Offer price", money(offer)]], 9.6, 1.5, 3.3, [2.2, 1.6], 10, bold_rows=(3,), rowh=0.4)
        d.notes(s, ["Enterprise value = equity value (share price × shares outstanding) plus debt, noncontrolling interests and preferred, less cash. Market data as of " + co["as_of"] + "; balance sheets and LTM results from each company's latest SEC filings.",
                    "No company used in this analysis is identical to the Company. Multiples above the NM threshold or with negative denominators are shown as NM and excluded."], 6.1)

    def p_dcf():
        s = d.slide("Discounted Cash Flow Analysis", "dcf", "($ in millions, except per-share data)")
        pv = g("row_pv")[0]
        rows = [["Fiscal year"] + ylab[1:], ["Unlevered free cash flow"] + [mmf(x) for x in uf[1:]], ["Cash flow in period (stub for first year)"] + [mmf(x) for x in g("row_ufcf_p")[0][1:]],
                ["Discount factor"] + [f"{x:.3f}" for x in g("row_df")[0][1:]], ["Present value"] + [mmf(x) for x in pv[1:]]]
        d.table(s, rows, 0.5, 1.5, 8.0, [3] + [1] * (len(ylab) - 1), 10, bold_rows=(4,), rowh=0.34)
        rows = [["", "Perpetuity growth", "Exit multiple"], ["WACC (midpoint)", pct(g("wacc_dcf_perp")), pct(g("wacc_dcf_exit"))], ["Terminal assumption", pct(g("g_mid")), mult(g("exit_mid"))],
                ["Enterprise value ($mm)", mmf(g("ev_perp")), mmf(g("ev_exit"))], ["Terminal value % of EV", pct(g("tv_share_perp")), pct(g("tv_share_exit"))],
                ["Implied exit multiple / perpetuity growth", mult(g("implied_perp")), pct(g("implied_exit"))], ["Implied value per share (midpoint)", money(g("dcf_ps_mid_perp")), money(g("dcf_ps_mid_exit"))],
                ["Selected range per share", f"{money(R['dcf_pgr']['low'])} – {money(R['dcf_pgr']['high'])}", f"{money(R['dcf_exit']['low'])} – {money(R['dcf_exit']['high'])}"],
                [f"Reverse DCF: implied by the unaffected price ({money(g('px_unaff'))})", pct(g("rdcf_g")), mult(g("rdcf_x"))]]
        d.table(s, rows, 0.5, 3.3, 8.0, [3, 1.6, 1.6], 10, bold_rows=(6, 7), shade_rows=(7,), rowh=0.3)
        d.text(s, 8.9, 1.5, 4.0, 4.2, ["Methodology", f"Unlevered free cash flows for the fiscal years {ylab[1]} through {ylab[-1]} discounted to {date} using a mid-year convention, with the first year prorated for the stub period.",
                f"Discount rates of {pct(g('wacc') - g('wacc_step'))} to {pct(g('wacc') + g('wacc_step'))}, based on a weighted average cost of capital of {pct(g('wacc'))} (see appendix).",
                f"Terminal value by perpetuity growth rates of {pct(g('g_mid') - g('g_step'))} to {pct(g('g_mid') + g('g_step'))}, and by exit multiples of {mult(g('exit_mid') - g('exit_step'))} to {mult(g('exit_mid') + g('exit_step'))} terminal-year EBITDA (selected public companies median {mult(g('comps_median_ebitda'))}; {t['ticker']} at the unaffected price {mult(g('tgt_ev_ltm_ebitda_unaff'))} LTM EBITDA).",
                f"Reverse DCF: at the midpoint WACC, the unaffected price implies {pct(g('rdcf_g'))} perpetuity growth or a {mult(g('rdcf_x'))} exit multiple on the same cash flows.",
                f"Enterprise value less net debt, noncontrolling interests and preferred stock ({mmf(-g('net_adj'))} $mm), divided by {g('shares'):,.1f} million shares."], 10)

    def p_sens():
        s = d.slide("Discounted Cash Flow Analysis — Sensitivity", "sensitivity", "Implied value per share at various WACC and terminal value assumptions")
        for key, lab, fx, x in [("sens_pgr", "Perpetuity growth rate", pct, 0.5), ("sens_exit", "Exit multiple (EV / EBITDA)", mult, 6.9)]:
            gr_ = g(key); rows = [["WACC \\ " + lab] + [fx(v) for v in gr_[0][1:]]] + [[pct(r_[0])] + [money(v) for v in r_[1:]] for r_ in gr_[1:]]
            d.table(s, rows, x, 1.6, 5.9, [1.6] + [1] * 5, 10, shade_rows=(3,) if st["table"].get("grid_mid_fill", True) else (), rowh=0.4, align_first=PP_ALIGN.CENTER)
        d.notes(s, [("Shaded row is the midpoint WACC; t" if st["table"].get("grid_mid_fill", True) else "The middle row is the midpoint WACC; t") + "he center cell equals the midpoint value on the prior page. Selected ranges use the midpoint WACC ± one step and the terminal assumption ± one step."], 4.4, 10)

    def p_lbo():
        s = d.slide("Leveraged Buyout Analysis", "lbo", "Illustrative ability of a financial sponsor to pay, based on the illustrative projections")
        rows = [["Key assumptions", ""], ["Total leverage (x LTM EBITDA)", mult(g("lbo_lev"))], ["Blended interest rate", pct(g("lbo_rate"))], ["Exit multiple (EV / EBITDA)", mult(g("lbo_exit"))],
                ["Holding period", f"{g('hold')} years"], ["Fees and expenses", pct(g("lbo_fees")) + " of EV"], ["Target IRR", f"{pct(g('irr_lo'), 0)} – {pct(g('irr_hi'), 0)}"]]
        d.table(s, rows, 0.5, 1.6, 5.6, [3, 2], 11, rowh=0.38)
        rows = [["Results", f"{pct(g('irr_hi'), 0)} IRR", f"{pct(g('irr_lo'), 0)} IRR"], ["Implied EV / LTM EBITDA", mult(g("lbo_mult_b")), mult(g("lbo_mult_a"))],
                ["Implied value per share", money(R["lbo"]["low"]), money(R["lbo"]["high"])], ["Offer price", money(offer), money(offer)]]
        d.table(s, rows, 6.6, 1.6, 6.2, [3, 1.6, 1.6], 11, bold_rows=(2,), shade_rows=(2,), rowh=0.42)
        d.notes(s, ["Debt is assumed outstanding at the opening balance for interest purposes; levered free cash flow repays debt. Sponsor equity at entry is the exit equity value discounted at the target IRR."], 4.6, 10)

    def p_prem():
        s = d.slide("Premiums Paid Analysis", "premiums", "Illustrative range of premiums applied to the unaffected share price")
        d.table(s, [["", "Low", "High"], ["Premium to unaffected price", pct(g("prem_lo"), 0), pct(g("prem_hi"), 0)], ["Unaffected share price", money(g("px_unaff")), money(g("px_unaff"))],
                    ["Implied value per share", money(R["premiums"]["low"]), money(R["premiums"]["high"])], ["Offer price premium to unaffected price", pct(g("prem_unaff")), ""]], 0.5, 1.6, 8.0, [3, 1.5, 1.5], 12, bold_rows=(3,), shade_rows=(3,), rowh=0.45)
        d.notes(s, [f"The premium range is an illustrative judgment input ({b['prem']}). A full analysis would apply premiums observed in comparable acquisitions of U.S. public companies."], 4.3, 10)

    def p_wacc():
        s = d.slide("Appendix: Weighted Average Cost of Capital Analysis", "wacc", "Capital asset pricing model with peer betas unlevered and relevered at the target capital structure")
        rows = [["Component", "Value"], ["Risk-free rate", pct(g("rf"), 2)], ["Equity risk premium", pct(g("erp"))], ["Size premium", pct(g("size"))],
                ["Unlevered beta, peer median", beta(C.get("beta_u_peers", {}).get("value"))], [f"Unlevered beta, {t['name']}", beta(C.get("beta_u_own", {}).get("value"))], ["Unlevered beta (selected)", f"{g('beta_u'):.2f}"],
                ["Target debt / total capitalization", pct(g("dcap"), 0)], ["Relevered beta", f"{g('beta_l'):.2f}"], ["Cost of equity", pct(g("ke"))], ["Pre-tax cost of debt", pct(g("kd"))],
                ["After-tax cost of debt", pct(g("kd_at"))], ["Weighted average cost of capital", pct(g("wacc"))]]
        d.table(s, rows, 0.5, 1.5, 6.0, [3, 1.5], 11, bold_rows=(12,), shade_rows=(12,), rowh=0.33)
        d.text(s, 7.0, 1.5, 5.8, 4, [f"Risk-free rate: {co['market']['risk_free'].get('source', '')}.", f"Betas: {t['price'].get('beta_basis', '')}, unlevered with the Hamada formula at a {pct(g('tax_m'), 0)} marginal tax rate"
                + (f", with a debt beta of {g('debt_beta'):.2f} for issuers above {g('hy_lev'):.1f}x debt / LTM EBITDA (treated as high yield)." if "debt_beta" in C else "."),
                f"Equity risk premium: {b['erp']}.", f"Cost of debt: {b['kd']}."], 10, False, st["text"]["muted"])

    # the judgment calls: each EBITDA definition the data supports, and each discount-rate input, each its own recalculated workbook
    allc = val.get("cases") or {}; ecases = {k: v for k, v in allc.items() if "+" not in k}; wks = [k for k in allc if "+" in k]
    def crng(CC, k, a): return f"{money(CC[k]['ranges'][a]['low'])} – {money(CC[k]['ranges'][a]['high'])}"
    def ccell(CC, k, c): return (CC[k]["cells"].get(c) or {}).get("value")
    def beta(x): return f"{x:.2f}" if isinstance(x, (int, float)) else "–"

    def p_ebitda_cases():
        s = d.slide("EBITDA Definition: Judgment Calls", None, "Implied value per share under each EBITDA definition; the base case is the first column")
        short = {"reported": "Reported (SBC as a cash cost)", "ex_sbc": "SBC added back", "management": "Management adjusted"}
        ks = [k for k in ("reported", "ex_sbc", "management") if k in ecases]; cv = lambda k, c: ccell(ecases, k, c)
        rows = [[""] + [short[k] for k in ks], ["LTM EBITDA ($mm)"] + [mmf(cv(k, "h_ebitda_ltm")) for k in ks],
                [f"{t['name']} EV / LTM EBITDA at the unaffected price"] + [mult(cv(k, "tgt_ev_ltm_ebitda_unaff")) for k in ks],
                ["Selected EV / LTM EBITDA multiples"] + [f"{mult(cv(k, 'comps_lo'))}–{mult(cv(k, 'comps_hi'))}" for k in ks], ["WACC (midpoint)"] + [pct(cv(k, "wacc")) for k in ks],
                ["Selected Public Companies Analysis"] + [crng(ecases, k, "comps") for k in ks], ["Discounted Cash Flow Analysis — perpetuity growth"] + [crng(ecases, k, "dcf_pgr") for k in ks],
                ["Discounted Cash Flow Analysis — exit multiple"] + [crng(ecases, k, "dcf_exit") for k in ks], ["Leveraged Buyout Analysis"] + [crng(ecases, k, "lbo") for k in ks],
                ["Offer price per share"] + [money(offer)] * len(ks)]
        d.table(s, rows, 0.5, 1.6, 12.3, [5] + [3] * len(ks), 11, bold_rows=(len(rows) - 1,), rowh=0.38)
        d.notes(s, [ecases[k]["label"] + "." for k in ks] + ["Trading range and premiums do not depend on the EBITDA definition. Each column is a separate model workbook (cases/<case>/model.xlsx)."], 5.55)

    def p_wacc_cases():
        base = wks[0].split("+")[0]; ks = [base] + wks
        s = d.slide("Discount Rate: Judgment Calls", None, f"Implied value per share as each WACC input changes; EBITDA on the {base.replace('_', ' ')} basis throughout")
        short = {"own_beta": "Target's own beta", "long_rf": "Long-bond risk-free", "erp_high": "ERP 6.5%", "combined": "All three"}
        cv = lambda k, c: ccell(allc, k, c)
        rows = [[""] + ["Base WACC"] + [short[k.split("+")[1]] for k in wks], ["Risk-free rate"] + [pct(cv(k, "rf"), 2) for k in ks], ["Equity risk premium"] + [pct(cv(k, "erp")) for k in ks],
                ["Unlevered beta"] + [beta(cv(k, "beta_u")) for k in ks], ["Relevered beta"] + [beta(cv(k, "beta_l")) for k in ks],
                ["Cost of equity"] + [pct(cv(k, "ke")) for k in ks], ["WACC (midpoint)"] + [pct(cv(k, "wacc")) for k in ks],
                ["Discounted Cash Flow Analysis — perpetuity growth"] + [crng(allc, k, "dcf_pgr") for k in ks], ["Discounted Cash Flow Analysis — exit multiple"] + [crng(allc, k, "dcf_exit") for k in ks],
                ["Offer price per share"] + [money(offer)] * len(ks)]
        d.table(s, rows, 0.5, 1.6, 12.3, [4.2] + [1.6] * len(ks), 10, bold_rows=(6, len(rows) - 1), rowh=0.36)
        d.notes(s, [f"{short[k.split('+')[1]]}: " + allc[k]["label"].split("; WACC with ")[-1] + "." for k in wks]
                + ["Each column is a separate model workbook (cases/<case>/model.xlsx). None of the alternative inputs is taken from the advisor."], 5.4, 9)

    judgment = ([p_ebitda_cases] if len(ecases) > 1 else []) + ([p_wacc_cases] if wks else [])
    return [("Transaction Overview", [p_overview, p_trading, p_projections]),
            ("Financial Analysis", [p_summary] + judgment + [p_comps, p_dcf, p_sens, p_lbo, p_prem]),
            ("Appendix", [p_wacc])]

def run(company_json, terms_json, valuation_json, out, log=print, house_style="auto"):
    co = need(load(company_json), "company", company_json); terms = need(load(terms_json), "deal_terms", terms_json); val = need(load(valuation_json), "valuation", valuation_json)
    st = load_style(house_style, terms.get("advisor")); FMT["spaced"] = st["numbers"]["spaced"]
    t = co["target"]; od = datetime.date.fromisoformat(terms["opinion_date"]); date = od.strftime("%B %-d, %Y")
    d = Deck(terms, t["name"], st); d.month_year = od.strftime("%B %Y")
    try:
        d.cover(date, t)
        if st["disclaimer_page"] == "front": d.disclaimer_page()
        sections = build_pages(d, co, terms, val, date)
        toc = d.slide((st.get("toc_opts") or {}).get("title", "Table of Contents")) if st.get("toc") else None
        starts = []; dv = st["dividers"]["style"]; num = 0
        for name, pages in sections:
            appendix = name == "Appendix"
            label = name if (appendix or not st["dividers"].get("numerals", True)) else (f"{ROMAN[num]}.  {name}" if dv in ("roman", "plain", "rules", "none", "appendix_only") else f"{num + 1}.  {name}")
            if not appendix: num += 1
            d.section = name
            if dv != "none" and (dv != "appendix_only" or appendix): d.divider(label)
            starts.append((label, d.n + (0 if dv != "none" and (dv != "appendix_only" or appendix) else 1)))
            for fn in pages: fn()
        d.section = None
        if st["disclaimer_page"] == "back": d.disclaimer_page()
        if toc is not None:
            d.toc_list(toc, starts, [n for n, _ in sections])
    finally:
        FMT["spaced"] = False
    out = Path(out); out.mkdir(parents=True, exist_ok=True); pp = out / "board_book.pptx"; d.p.save(pp); log(f"wrote {pp} ({d.n} slides, house style {st['key']})")
    pdf = to_pdf(pp, out, log)
    man = {"schema": SCHEMAS["deck"], "pptx": str(pp), "pdf": str(pdf) if pdf else None, "house_style": st["key"], "pages": d.index,
           "analyses": sorted({x["analysis"] for x in d.index if x["analysis"] and x["analysis"] not in ("summary", "wacc")})}
    save(man, out / "deck.json"); return man

def to_pdf(pptx, out, log=print):
    soffice = shutil.which("soffice") or shutil.which("libreoffice") or ("/Applications/LibreOffice.app/Contents/MacOS/soffice" if Path("/Applications/LibreOffice.app").exists() else None)
    if not soffice: log("LibreOffice not found: board_book.pdf not written; intake can read the .pptx directly"); return None
    prof = Path(tempfile.mkdtemp(prefix="lo_profile_"))
    subprocess.run([soffice, f"-env:UserInstallation={Path(prof).resolve().as_uri()}", "--headless", "--convert-to", "pdf", "--outdir", str(out), str(pptx)], capture_output=True, text=True, timeout=240)
    pdf = Path(out) / (Path(pptx).stem + ".pdf"); log(f"wrote {pdf}" if pdf.exists() else "PDF conversion failed"); return pdf if pdf.exists() else None

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("company"); ap.add_argument("terms"); ap.add_argument("valuation"); ap.add_argument("out")
    ap.add_argument("--house-style", default="auto", help="auto (match the advisor), default, or a profile in references/house-styles"); a = ap.parse_args()
    run(a.company, a.terms, a.valuation, a.out, house_style=a.house_style)
