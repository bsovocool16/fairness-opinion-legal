"""analyses.py: the analysis vocabulary and presented(), which decides what a filed section 'presents'."""
import re
import pytest
from analyses import ANALYSES, DECK_RX, HEAD, LABELS, NUMERIC, REF, VALUATION, presented

def test_vocabularies_cover_the_same_labels():
    assert set(ANALYSES) == set(DECK_RX) == set(LABELS)
    assert VALUATION <= set(LABELS) and "sensitivity" not in VALUATION
    assert {l for l, _ in HEAD} - {"other"} <= set(LABELS)

@pytest.mark.parametrize("rx", list(ANALYSES.values()) + list(DECK_RX.values()) + [r for _, r in HEAD])
def test_patterns_compile(rx):
    re.compile(rx, re.I)

@pytest.mark.parametrize("s", ["$35.00", "US$ 1", "C$2", "12.5%", "12 %", "9.1x", "10x", "HK$3"])
def test_numeric_matches_results(s):
    assert NUMERIC.search(s)

@pytest.mark.parametrize("s", ["2026", "Exhibit 99", "x-axis", "page 12", "the 10th"])
def test_numeric_ignores_bare_numbers(s):
    assert not NUMERIC.search(s)

def test_presented_needs_a_result_after_the_mention():
    assert presented("William Blair performed a discounted cash flow analysis that implied $30.00 to $40.00 per share.") == ["dcf"]
    assert presented("William Blair performed a discounted cash flow analysis.") == []

def test_presented_result_window_is_900_characters():
    near = "Discounted Cash Flow Analysis. " + "x" * 800 + " $1.00"
    far = "Discounted Cash Flow Analysis. " + "x" * 1000 + " $1.00"
    assert presented(near) == ["dcf"] and presented(far) == []

def test_presented_reads_every_analysis_and_is_sorted():
    text = ("Selected Public Companies Analysis: 8.0x to 10.0x. Selected Precedent Transactions Analysis: 9.5x. "
            "Discounted Cash Flow Analysis: $31.00. Leveraged Buyout Analysis: 20% IRR. Premiums Paid Analysis: 30%. "
            "52-week trading range $20.00 to $36.00. Analyst price targets $33.00. Sum-of-the-parts: $34.00.")
    got = presented(text)
    assert got == sorted(got)
    assert set(got) >= {"comps", "precedents", "dcf", "lbo", "premiums", "trading_range", "targets", "sotp"}

def test_reference_phrases():
    assert REF.search("This information was presented for reference purposes only.")
    assert REF.search("for illustrative purposes")
    assert not REF.search("William Blair relied on this analysis.")
