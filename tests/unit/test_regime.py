"""precedent_search.regime_of / infer_regime: Rule 13e-3 or conventional, from the form, the text or the buyer type."""
import pytest
from precedent_search import infer_regime, regime_of

def test_schedule_13e3_form_is_13e3_whatever_the_text():
    assert regime_of("SC 13E3", "") == "13e-3" and regime_of("sc 13e3/a", None) == "13e-3"

def test_proxy_needs_three_mentions():
    two = "Rule 13e-3 ... Schedule 13E-3"; three = two + " ... going-private transaction"
    assert regime_of("DEFM14A", two) == "conventional"
    assert regime_of("DEFM14A", three) == "13e-3"

@pytest.mark.parametrize("bt", ["controlling stockholder", "Management", "affiliate of the Company", "founder", "majority holder", "parent"])
def test_insider_buyer_is_13e3(bt):
    assert infer_regime("", bt) == "13e-3"

@pytest.mark.parametrize("bt", ["sponsor", "strategic", None, ""])
def test_outside_buyer_reads_the_text(bt):
    assert infer_regime("", bt) == "conventional"
    assert infer_regime("Rule 13e-3 transaction; see Schedule 13E-3", bt) == "13e-3"

def test_special_committee_with_rollover_is_13e3():
    assert infer_regime("The Special Committee considered the rollover by management.") == "13e-3"
    assert infer_regime("The Special Committee met.") == "conventional"

def test_example_deal_is_13e3():
    from conftest import EXAMPLE_RUN
    book = (EXAMPLE_RUN / "inputs" / "book.txt").read_text(errors="ignore")
    assert infer_regime(book[:300000], "sponsor") in ("13e-3", "conventional")   # the regime is asked at intake, never inferred; the hint must not crash
