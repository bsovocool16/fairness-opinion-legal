"""verify_candidates.section_of: cutting the advisor's section out of a whole proxy."""
from verify_candidates import section_of

FILLER = ("William Blair performed a selected public companies analysis that implied 8.0x to 10.0x. "
          "The discounted cash flow analysis implied $30.00 to $38.00 per share. Premiums paid were 30%. ") * 70

def proxy(body=FILLER, after="Certain Unaudited Prospective Financial Information"):
    return ("TABLE OF CONTENTS\nOpinion of William Blair 45\nInterests of the Company's Directors 60\n"
            "SPECIAL FACTORS\nBackground of the Merger\n" + "The board met and discussed the proposal at length. " * 120 + "\n"
            f"Opinion of William Blair\nWilliam Blair was retained by the Special Committee to act as its financial advisor.\n{body}\n"
            f"{after}\nThe Company does not as a matter of course make projections.\n")

def test_cuts_the_real_section_not_the_contents_entry():
    sec = section_of(proxy(), ["William Blair"])
    assert sec.startswith("Opinion of William Blair\nWilliam Blair was retained")
    assert "Prospective Financial Information" not in sec and "TABLE OF CONTENTS" not in sec

def test_cross_reference_does_not_end_the_section():
    body = FILLER[:7000] + ' See the section entitled "Certain Unaudited Prospective Financial Information" below. ' + FILLER[:2000]
    sec = section_of(proxy(body), ["William Blair"])
    assert "See the section entitled" in sec

def test_no_heading_returns_none():
    assert section_of("A proxy with no advisor section at all.", ["William Blair"]) is None

def test_section_capped_at_90000_characters():
    sec = section_of(proxy(FILLER * 6, after=""), ["William Blair"])
    assert len(sec) <= 90000

import pytest
@pytest.mark.parametrize("heading", ["Certain Unaudited Prospective Financial Information", "Certain Prospective Financial Information",
                                     "Unaudited Prospective Financial Information", "Certain Unaudited Financial Projections",
                                     "Interests of the Company's Directors and Executive Officers in the Merger", "Appraisal Rights"])
def test_next_proxy_heading_ends_the_section(heading):
    sec = section_of(proxy(after=heading), ["William Blair"])
    assert heading not in sec and sec.rstrip().endswith("Premiums paid were 30%.")
