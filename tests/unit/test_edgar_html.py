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
