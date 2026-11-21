"""build_shell.py: segmenting a filed section by analysis heading, ranking bases, splicing donors, marking what the book lacks."""
import json
import pytest
import build_shell as BS

def test_heading_of():
    assert BS.heading_of("Selected Public Companies Analysis") == "comps"
    assert BS.heading_of("Discounted Cash Flow Analysis.  William Blair calculated...") == "dcf"
    assert BS.heading_of("William Blair performed a discounted cash flow analysis of the Company using the projections and a range of discount rates.") is None   # prose, not a heading
    assert BS.heading_of("What is a discounted cash flow analysis?") is None
    assert BS.heading_of("Other Factors") == "other"

SECTION = """Opinion of Acme
Acme was retained by the board.
The following is a summary of the material financial analyses performed by Acme.
Selected Public Companies Analysis
Acme reviewed companies and applied 8.0x to 10.0x.
Discounted Cash Flow Analysis
Acme calculated $30.00 to $40.00 per share.
General
The preparation of a fairness opinion is a complex process.
Acme is entitled to a fee of $2 million."""

def test_segment():
    front, segs, back = BS.segment(SECTION)
    assert front.startswith("Opinion of Acme") and "summary of the material" in front
    assert [l for l, _ in segs] == ["comps", "dcf", "other"]        # a bare "General" heading is an "other" segment
    assert back.startswith("The preparation of a fairness opinion") and "entitled to a fee" in back

def test_segment_without_headings_is_all_front():
    assert BS.segment("Just prose.\nMore prose.") == ("Just prose.\nMore prose.", [], "")

def donor(label_heading, body):
    return SECTION.replace("Discounted Cash Flow Analysis\nAcme calculated $30.00 to $40.00 per share.", f"{label_heading}\n{body}")

@pytest.mark.cli
def test_shell_marks_missing_and_borrows(run_script, make_deal):
    lbo = "Acme performed an illustrative leveraged buyout analysis assuming 20% to 25% returns and 5.0x leverage. " * 6
    d = make_deal(facts={"advisor": "Acme", "opinion_date": "2026-05-01", "regime": "conventional"}, deck={"comps": "core", "lbo": "core"},
                  precedents={"base": SECTION, "donor": donor("Leveraged Buyout Analysis", lbo)},
                  index=[{"acc": "base", "presented": ["comps", "dcf"], "regime": "conventional", "date": "2025-01-01"}, {"acc": "donor", "presented": ["comps", "lbo"], "date": "2019-01-01"}])
    run_script("build_shell.py", d, "--base", "base")
    rat = json.loads((d / "shell" / "rationale.json").read_text()); comp = (d / "shell" / "shell_composite.txt").read_text()
    assert rat["selected"] == "base"
    assert "[[NOT IN THIS BOOK" in comp and "[[BORROWED FROM donor: lbo paragraphs" in comp
    elig = (d / "shell" / "shell_composite_eligible.txt").read_text()
    assert "[[" not in elig and "Discounted Cash Flow" not in elig and "leveraged buyout" in elig

@pytest.mark.cli
def test_base_override(run_script, make_deal):
    d = make_deal(facts={}, deck={"comps": "core"}, precedents={"a": SECTION, "b": SECTION.replace("Acme", "Bcme")})
    run_script("build_shell.py", d, "--base", "b")
    assert json.loads((d / "shell" / "rationale.json").read_text())["selected"] == "b"

@pytest.mark.cli
def test_no_precedents_exits_cleanly(run_script, make_deal):
    r = run_script("build_shell.py", make_deal(facts={}, deck={"comps": "core"}), check=False)
    assert r.returncode != 0 and "no precedents" in r.stderr and "Traceback" not in r.stderr
