"""Properties of the text and table parsers, on generated proxy text, HTML and EDGAR tables."""
import html as H
import re
import pytest
from hypothesis import assume, example, given, strategies as st
import edgar_precedents as EP
from analyses import ANALYSES, presented
from bankname import bank_key
from precedent_search import infer_regime, regime_of
from verify_candidates import section_of
import defined_terms as DT
import classify_book as CB
from strategies import edgar_fragments, financial_figure, label, text_soup

pytestmark = pytest.mark.fuzz

@given(st.lists(st.tuples(label, st.lists(financial_figure(), min_size=1, max_size=6)), min_size=1, max_size=6), st.booleans())
def test_edgar_table_cells_reassemble(rows, spacers):
    """Every figure EDGAR split over several cells comes back as one cell, in order, after the row label."""
    # "(3)" alone is ambiguous: a footnote marker or a negative 3. table_rows reads it as a footnote (see the xfail below), so the
    # property excludes it.
    assume(not any(re.fullmatch(r"\(\d{1,2}\)", f) for _, v in rows for f in v))
    width = max(len(v) for _, v in rows); rows = [(l, (v + ["NM"] * width)[:width]) for l, v in rows]
    def td(c): return f"<td>{H.escape(c)}</td>" + ("<td>&nbsp;</td>" if spacers else "")
    html = "<tr><td>Company</td>" + "".join(f"<td>Col {i}</td>" for i in range(width)) + "</tr>"
    for l, vals in rows: html += "<tr>" + td(l) + "".join(td(f) for v in vals for f in edgar_fragments(v)) + "</tr>"
    out = EP.table_rows(html)
    assert out[0] == ["Company"] + [f"Col {i}" for i in range(width)]
    assert out[1:] == [[l] + vals for l, vals in rows]

@pytest.mark.xfail(strict=True, reason="FINDING: a small negative written as (3) in its own cell is read as a footnote marker and glued "
                   "onto the cell before it. EDGAR uses the same form for both; a fix needs a rule (for example: a column whose other cells are "
                   "figures holds a figure).")
def test_small_parenthesized_negative_stays_a_value():
    rows = EP.table_rows("<tr><td>Item</td><td>2025</td><td>2026</td></tr><tr><td>Net income</td><td>(3)</td><td>12</td></tr>")
    assert rows[1] == ["Net income", "(3)", "12"]

@given(st.lists(st.text(max_size=8), max_size=12))
def test_glue_keeps_every_character_and_drops_empties(cells):
    out = EP._glue(cells)
    assert all(out) and "".join(out).replace(" ", "") == "".join(cells).replace(" ", "")

@given(st.recursive(st.one_of(text_soup, financial_figure()),
                    lambda inner: st.tuples(st.sampled_from(["p", "div", "table", "tr", "td", "th", "span", "b", "br", "script", "li", "font"]), st.lists(inner, max_size=4))
                    .map(lambda t: f"<{t[0]} colspan=\"{len(t[1])}\">" + "".join(map(str, t[1])) + f"</{t[0]}>"), max_leaves=25))
def test_html_to_text_total_and_clean(h):
    t = EP.html_to_text(str(h))
    assert "\n\n" not in t and "\xa0" not in t and "​" not in t and "<td" not in t

@given(text_soup)
def test_presented_is_a_sorted_subset(t):
    got = presented(t); assert got == sorted(set(got)) and set(got) <= set(ANALYSES)

@given(text_soup, st.one_of(st.none(), st.text(max_size=20)), st.one_of(st.none(), st.sampled_from(["DEFM14A", "SC 13E3", "SC 14D9", ""])))
def test_regime_is_always_one_of_two(t, buyer, form):
    assert infer_regime(t, buyer) in ("13e-3", "conventional") and regime_of(form, t) in ("13e-3", "conventional")

@given(st.one_of(st.none(), st.text(max_size=40)))
def test_bank_key_total(n):
    k = bank_key(n); assert k and re.fullmatch(r"[a-z]+", k)

@given(text_soup)
@example("Opinion of William Blair\n" + "discounted cash flow $1 " * 3000)
def test_section_of_total(t):
    sec = section_of(t, ["William Blair"])
    assert sec is None or (len(sec) <= 90000 and re.match(r"(?i)(opinion|summary|financial analyses|fairness opinion)", sec))

@given(text_soup)
def test_classify_book_total(t):
    for k, rec in CB.classify(t).items():
        assert k in ANALYSES and rec["status"] in ("core", "reference", "grid") and rec["pages"] == sorted(rec["pages"])
        assert all(1 <= p <= t.count("-----PAGE-----") + 1 for p in rec["pages"])

@given(text_soup)
def test_glossary_terms_unique_and_capitalized(t):
    g = DT.glossary(DT.clean(t)); terms = [x["term"] for x in g]
    assert len(terms) == len(set(terms)) and all(x[:1].isupper() and len(x) <= 70 for x in terms)
    assert all(len(x["definition"]) <= 450 for x in g)
