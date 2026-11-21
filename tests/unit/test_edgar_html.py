"""edgar_precedents: EDGAR table cleanup and HTML-to-text (no network)."""
import pytest
from edgar_precedents import _glue, has_section, html_to_text, merged, norm, table_rows

def tr(*cells): return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"

@pytest.mark.parametrize("cells,want", [
    (["$", "273"], ["$273"]), (["(0.7", "%)"], ["(0.7%)"]), (["9.1x", "(3)"], ["9.1x (3)"]), (["", "a", "", "b"], ["a", "b"]),
    (["12.5", "%"], ["12.5%"]), (["$(", "1,234", ")"], ["$(1,234)"]), (["NM"], ["NM"]),
])
def test_glue(cells, want):
    assert _glue(cells) == want

def test_table_rows_header_then_values():
    rows = table_rows(tr("Company", "EV/EBITDA") + tr("Alpha Inc.", "9.1", "x") + tr("Beta Corp.", "$", "10.2"))
    assert rows == [["Company", "EV/EBITDA"], ["Alpha Inc.", "9.1x"], ["Beta Corp.", "$10.2"]]

def test_table_rows_colspan_and_spacers():
    rows = table_rows('<tr><td colspan="2">Metric</td><td></td><td>Low</td><td>High</td></tr>' + tr("EBITDA", "", "8.0x", "", "10.0x"))
    assert rows[1] == ["EBITDA", "8.0x", "10.0x"]

def test_stacked_header_folds_group_label_onto_first_subcolumn():
    html = ('<tr><td></td><td colspan="2">Enterprise Value / EBITDA</td></tr>'
            "<tr><td>Company</td><td>2026E</td><td>2027E</td></tr>" + tr("Alpha", "9.0x", "8.0x"))
    rows = table_rows(html)
    assert rows[-1] == ["Alpha", "9.0x", "8.0x"]
    assert any("Enterprise Value / EBITDA" in c for c in rows[0])

def test_footnote_layout_table_becomes_prose():
    assert table_rows(tr("(1)", "Excludes one-time items.")) == [["(1) Excludes one-time items."]]
    assert table_rows(tr("•", "a bullet")) == [["• a bullet"]]

def test_table_rows_empty():
    assert table_rows("") == [] and table_rows("<tr><td> </td></tr>") == []

def test_html_to_text_keeps_paragraphs_and_rows():
    h = ("<html><style>p{}</style><script>x()</script><p>Opinion of William&nbsp;Blair</p><div>First&#8203; para.</div>"
         "<table>" + tr("Company", "Multiple") + tr("Alpha", "9.0x") + "</table><p>After.</p></html>")
    t = html_to_text(h)
    lines = [l.strip() for l in t.split("\n") if l.strip()]
    assert lines[0] == "Opinion of William Blair" and "First para." in lines
    assert "| Company | Multiple |" in lines and "| Alpha | 9.0x |" in lines
    assert "x()" not in t and "p{}" not in t and "​" not in t and "\xa0" not in t

def test_norm_and_merged():
    assert norm("Opinion of  J.P. Morgan!") == "opinion of j p morgan"
    m = merged([[{"acc": "1", "v": "a"}], [{"acc": "1", "v": "b"}, {"acc": "2", "v": "c"}]])
    assert list(m) == ["1", "2"] and m["1"]["v"] == "a"

def test_has_section():
    assert has_section("... Opinion of William Blair ...", ["William Blair"]) == "heading"
    assert has_section("William Blair rendered its oral opinion to the board", ["William Blair"]) == "opinion text"
    assert has_section("nothing here", ["William Blair"]) is None

# ---- (n): a footnote marker or a small negative number. Default number; footnote only when a signal says so.
HEAD = "<tr><td>Item</td><td>2025</td><td>2026</td></tr>"

def test_bare_parenthesized_integer_is_a_number_by_default():
    assert table_rows(HEAD + tr("Net income", "(3)", "12"))[1] == ["Net income", "(3)", "12"]

@pytest.mark.parametrize("cell", ["<td><sup>(1)</sup></td>", '<td style="vertical-align:super">(1)</td>', '<td style="font-size:6pt">(1)</td>',
                                  '<td><font style="font-size:70%">(1)</font></td>'])
def test_superscript_or_small_font_is_a_footnote(cell):
    assert table_rows(HEAD + f"<tr><td>Revenue</td>{cell}<td>12</td><td>14</td></tr>")[1] == ["Revenue (1)", "12", "14"]

def test_columns_decide_marker_after_label():
    rows = table_rows(HEAD + tr("Revenue", "10", "11") + tr("EBITDA", "(1)", "4", "5"))
    assert rows[2] == ["EBITDA (1)", "4", "5"]

def test_columns_decide_marker_trailing_a_value():
    rows = table_rows(HEAD + tr("Revenue", "10", "11") + tr("EBITDA", "4", "(2)", "5"))
    assert rows[2] == ["EBITDA", "4 (2)", "5"]

def test_columns_keep_a_negative_and_glue_a_marker_in_one_row():
    rows = table_rows(HEAD + tr("Revenue", "10", "11") + tr("Net income", "(3)", "(1)", "7"))
    assert rows[2] in (["Net income", "(3) (1)", "7"], ["Net income (3)", "(1)", "7"])   # both line up: see the review test below

def test_note_text_below_the_table_decides_when_columns_cannot():
    table = "<table>" + tr("Alpha", "(1)", "5") + tr("Beta", "(2)", "6") + "</table>"
    review = []; plain = html_to_text(table, review=review)
    assert "| Alpha | (1) | 5 |" in plain and len(review) == 2                     # no header, no notes: numbers, flagged
    review = []; noted = html_to_text(table + "<p>(1) Excludes one-time items.</p><p>(2) Pro forma.</p>", review=review)
    assert "| Alpha (1) | 5 |" in noted and "| Beta (2) | 6 |" in noted and review == []

def test_note_rows_inside_the_table_count_as_notes():
    rows = table_rows(tr("Alpha", "(1)", "5") + tr("(1)", "Excludes one-time items."))
    assert rows == [["Alpha (1)", "5"], ["(1) Excludes one-time items."]]

def test_undecided_cells_are_reported():
    review = []
    rows = table_rows(HEAD + tr("Revenue", "10", "11") + tr("Net income", "(3)", "(1)", "7"), review=review)
    assert review and all(r["row"] == "Net income" and r["why"] for r in review)

def test_marker_inside_a_cell_is_left_alone():
    assert table_rows(HEAD + tr("Revenue (1)", "1,234(1)", "12"))[1] == ["Revenue (1)", "1,234(1)", "12"]

def test_letter_markers_stay_footnotes():
    assert table_rows(HEAD + tr("Revenue", "10", "(a)", "11"))[1] == ["Revenue", "10 (a)", "11"]

# ---- the review list, carried from the fetch to precedents/footnote_review.json
import json
import edgar_precedents as EP
import precedent_search as PS

def test_fetch_doc_records_undecided_cells(monkeypatch):
    page = "<table><tr><td>Alpha</td><td>(1)</td><td>5</td></tr></table>"
    class R: status_code = 200; text = page
    monkeypatch.setattr(EP.requests, "get", lambda *a, **k: R()); monkeypatch.setattr(EP, "GAP", 0); monkeypatch.setattr(EP, "FOOTNOTE_REVIEW", {})
    EP.fetch_doc(1, "0000000001-26-000001", "d.htm")
    assert EP.FOOTNOTE_REVIEW["0000000001-26-000001"] == [{"doc": "d.htm", "row": "Alpha", "cell": "(1)", "read_as": "number", "why": EP.FOOTNOTE_REVIEW["0000000001-26-000001"][0]["why"]}]

def test_write_footnote_review(tmp_path):
    (tmp_path / "A.txt").write_text("Opinion\n| Alpha | (1) | 5 |\n"); (tmp_path / "B.txt").write_text("Opinion\n| Beta | 4 |\n")
    collected = {"A": [{"doc": "a.htm", "row": "Alpha", "cell": "(1)"}, {"doc": "a.htm", "row": "Elsewhere", "cell": "(2)"}],
                 "B": [], "DROPPED": [{"doc": "x", "row": "Alpha", "cell": "(1)"}]}
    cells = PS.write_footnote_review(tmp_path, [{"acc": "A"}, {"acc": "B"}], collected)
    assert cells == [{"acc": "A", "doc": "a.htm", "row": "Alpha", "cell": "(1)"}]            # only cells inside saved sections of kept filings
    assert json.loads((tmp_path / "footnote_review.json").read_text())["cells"] == cells

def test_write_footnote_review_empty_and_add_keeps_earlier(tmp_path):
    (tmp_path / "A.txt").write_text("| Alpha | (1) | 5 |\n")
    assert PS.write_footnote_review(tmp_path, [], {}) == [] and json.loads((tmp_path / "footnote_review.json").read_text())["cells"] == []
    PS.write_footnote_review(tmp_path, [{"acc": "A"}], {"A": [{"doc": "a", "row": "Alpha", "cell": "(1)"}]})
    (tmp_path / "C.txt").write_text("| Gamma | 1 |\n")
    cells = PS.write_footnote_review(tmp_path, [{"acc": "A"}, {"acc": "C"}], {"C": []})             # a later --add run
    assert [c["acc"] for c in cells] == ["A"]
