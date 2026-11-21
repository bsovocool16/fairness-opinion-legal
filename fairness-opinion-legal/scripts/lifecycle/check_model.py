#!/usr/bin/env python3
"""Audit an Excel model against banker drafting conventions: python3 check_model.py <model.xlsx> [--values <recalculated copy>] [--json]

Rules (references/lifecycle.md), each finding naming the cell:
  C1 color: a typed number or date is blue; a formula is black, or green when it references another tab; no formula is blue
  C2 no hardcodes in formulas: a formula carries no numeric literal other than the structural constants 0, 1, 2, 3, 4, 0.5, 12, 365
  C3 input placement: typed numbers appear only on the input tabs (Assumptions, Historicals, Comps, WACC)
  C4 units: every tab other than Cover states its units in B2
  C5 no errors: after recalculation no cell holds #DIV/0!, #REF!, #NAME?, #VALUE!, #N/A, #NUM! or a LibreOffice Err:5xx
  C6 no orphan inputs: every input on Assumptions is referenced by some formula
Exit status 1 when any rule fails. Usable on any workbook, not only the ones build_model.py writes."""
import sys, re, json, argparse
from openpyxl import load_workbook
INPUT_TABS = {"Assumptions", "Historicals", "Comps", "WACC"}
ALLOWED = {0.0, 1.0, 2.0, 3.0, 4.0, 0.5, 12.0, 365.0}
BLUE, GREEN = "0000FF", "008000"
ERR = re.compile(r"^(#DIV/0!|#REF!|#NAME\?|#VALUE!|#N/A|#NUM!|#NULL!|Err:\d{3})$")
REF = re.compile(r"(?:'[^']+'|[A-Za-z_][\w\.]*)!\$?[A-Z]{1,3}\$?\d+")
STRIP = re.compile(r"\"[^\"]*\"|(?:'[^']+'|[A-Za-z_][\w\.]*)!\$?[A-Z]{1,3}\$?\d+(?::\$?[A-Z]{1,3}\$?\d+)?|\$?[A-Z]{1,3}\$?\d+(?::\$?[A-Z]{1,3}\$?\d+)?|[A-Z][A-Z0-9\.]*\(")
NUM = re.compile(r"(?<![A-Za-z_\$\d\.])(\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)%?")

def color(cell):
    c = cell.font.color if cell.font else None
    if c is None or c.rgb is None or not isinstance(c.rgb, str): return "000000"
    return c.rgb[-6:].upper()

def check(path, values=None):
    wb = load_workbook(path); F = []
    refs_to = set()
    for ws in wb.worksheets:
        if ws.title != "Cover" and not (isinstance(ws["B2"].value, str) and re.search(r"million|thousand|billion|\$ in|units", ws["B2"].value, re.I)):
            F.append(("C4", f"{ws.title}!B2", "no units line"))
        for row in ws.iter_rows():
            for c in row:
                v = c.value; addr = f"{ws.title}!{c.coordinate}"
                if v is None: continue
                if isinstance(v, str) and v.startswith("="):
                    cross = bool(REF.search(v)); col = color(c)
                    for m in REF.finditer(v): refs_to.add(m.group(0).replace("$", "").replace("'", ""))
                    for m in re.finditer(r"(?<![!\w\$])\$?([A-Z]{1,3})\$?(\d+)(?::\$?([A-Z]{1,3})\$?(\d+))?", STRIP.sub(lambda m: m.group(0) if "!" not in m.group(0) and not m.group(0).endswith("(") and not m.group(0).startswith('"') else " ", v)):
                        refs_to.add(f"{ws.title}!{m.group(1)}{m.group(2)}")
                    for m in re.finditer(r"(?:'([^']+)'|([A-Za-z_][\w\.]*))!\$?([A-Z]{1,3})\$?(\d+):\$?([A-Z]{1,3})\$?(\d+)", v):
                        sh = m.group(1) or m.group(2); from openpyxl.utils import column_index_from_string as ci, get_column_letter as gl
                        for rr in range(int(m.group(4)), int(m.group(6)) + 1):
                            for cc in range(ci(m.group(3)), ci(m.group(5)) + 1): refs_to.add(f"{sh}!{gl(cc)}{rr}")
                    if col == BLUE: F.append(("C1", addr, f"formula in blue (inputs only): {v[:60]}"))
                    elif cross and col != GREEN: F.append(("C1", addr, f"cross-tab formula not green: {v[:60]}"))
                    elif not cross and col == GREEN: F.append(("C1", addr, f"same-tab formula in green: {v[:60]}"))
                    body = STRIP.sub(" ", v[1:])
                    for m in NUM.finditer(body):
                        x = float(m.group(1)) / (100 if m.group(0).endswith("%") else 1)
                        if x not in ALLOWED: F.append(("C2", addr, f"hardcoded {m.group(0)} in {v[:70]}"))
                elif isinstance(v, (int, float)) and not isinstance(v, bool) or hasattr(v, "year"):
                    if color(c) != BLUE: F.append(("C1", addr, f"typed number not blue: {v}"))
                    if ws.title not in INPUT_TABS: F.append(("C3", addr, f"typed number outside the input tabs: {v}"))
    if "Assumptions" in wb.sheetnames:
        ws = wb["Assumptions"]
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, (int, float)) and not isinstance(c.value, bool) or hasattr(c.value, "year"):
                    if f"Assumptions!{c.coordinate}" not in refs_to: F.append(("C6", f"Assumptions!{c.coordinate}", f"input {c.value} is not used by any formula"))
    if values:
        wv = load_workbook(values, data_only=True)
        for ws in wv.worksheets:
            for row in ws.iter_rows():
                for c in row:
                    if isinstance(c.value, str) and ERR.match(c.value.strip()): F.append(("C5", f"{ws.title}!{c.coordinate}", c.value))
    return F

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("model"); ap.add_argument("--values", default=None); ap.add_argument("--json", action="store_true"); a = ap.parse_args()
    F = check(a.model, a.values)
    if a.json: print(json.dumps([{"rule": r, "cell": c, "detail": d} for r, c, d in F], indent=1))
    else:
        by = {}
        for r, c, d in F: by.setdefault(r, []).append((c, d))
        for r in ("C1", "C2", "C3", "C4", "C5", "C6"):
            items = by.get(r, []); print(f"{r}: {'pass' if not items else f'{len(items)} finding(s)'}")
            for c, d in items[:15]: print(f"   {c}  {d}")
            if len(items) > 15: print(f"   ... {len(items) - 15} more")
    sys.exit(1 if F else 0)
