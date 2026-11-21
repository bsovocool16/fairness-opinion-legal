"""selfscore.py: the self-score a draft gets before review. Helpers in-process; whole-score checks on small synthetic deals."""
import json
import pytest
import selfscore as SS

def test_mask_given_names_and_numbers():
    t = SS.mask("William Blair & Company L.L.C. said William Blair paid $35.00 and 12.5%.", ["William Blair & Company L.L.C."])
    assert "William" not in t and "35" not in t and "12.5" not in t and t.count("NAME") == 2

def test_mask_lowercase_suffix_name():
    assert "Acme" not in SS.mask("Acme Widgets inc. paid", [])

@pytest.mark.xfail(strict=True, reason="FINDING: mask()'s generic company-name pattern is case-sensitive and its suffix list is lowercase, so "
                   "'Acme Holdings, Inc.' is never masked and unknown peer names count against advisor-language share. Fixing it changes "
                   "the scores calibrated in references/scoring.md, so it is left for a decision.")
def test_mask_names_with_capitalized_legal_suffix():
    assert "Acme" not in SS.mask("Acme Holdings, Inc. paid", [])

def test_m6_is_case_and_number_insensitive():
    a = SS.m6("The Company paid $35.00 per share in cash to the holders of record today", [])
    b = SS.m6("the company paid $41.10 per share in cash to the holders of record today", [])
    assert a == b and len(a) > 0

def test_cov():
    assert SS.cov(set(), {"x"}) is None and SS.cov({"a", "b"}, {"a"}) == 0.5

def test_tables_skip_separators():
    t = SS.tables("text\n| A | B |\n|---|---|\n| 1 | 2 |\nmore\n| C |\n")
    assert t == [[["A", "B"], ["1", "2"]], [["C"]]]

DRAFT = """Opinion of Acme Advisors

Acme Advisors performed a selected public companies analysis. The analysis implied 8.0x to 10.0x and $31.00 to $36.00 per share.

| Selected Company | EV / EBITDA |
|---|---|
| Alpha Holdings, Inc. | 9.0x |
| Beta Corp. | 8.5x |
| Gamma Industries | 10.0x |
| Median | 9.0x |

Acme Advisors also performed a discounted cash flow analysis implying $33.00 to $39.00 per share, and a premium of 99.9%.
"""

def score(run_script, d):
    run_script("selfscore.py", d, d / "draft" / "section.txt")
    return json.loads((d / "draft" / "selfscore.json").read_text())

@pytest.mark.cli
def test_numbers_not_in_inputs_flags_invented_figures(run_script, make_deal):
    book = "Selected Public Companies 8.0x 10.0x $31.00 $36.00 9.0x 8.5x\nDiscounted Cash Flow $33.00 $39.00"
    d = make_deal(facts={"advisor": "Acme Advisors", "target": "Target Co."}, book=book, draft=DRAFT, deck={"comps": "core", "dcf": "core"},
                  precedents={"p1": "Selected public companies analysis implied 9.0x. Discounted cash flow analysis implied $10.00."})
    s = score(run_script, d)
    assert s["numbers_checked"] == 11 and s["numbers_not_in_inputs_examples"] == ["99.9%"]
    assert s["presented"] == ["comps", "dcf"] and s["coverage"] == 1.0 and s["missing"] == []

@pytest.mark.cli
def test_peer_names_without_legal_suffix(run_script, make_deal):
    d = make_deal(facts={}, book="x", draft=DRAFT, deck={"comps": "core"})
    s = score(run_script, d)
    assert s["peer_names"] == 3 and s["peer_names_with_legal_suffix"] == 2 and s["peer_names_without_suffix"] == ["Gamma Industries"]

@pytest.mark.cli
def test_markers_and_commentary_are_caught(run_script, make_deal):
    draft = DRAFT + "\n[[BORROWED FROM x: dcf paragraphs]]\n[REVIEWER: confirm the fee]\nThis draft uses a placeholder for the date.\n"
    s = score(run_script, make_deal(facts={}, book="x", draft=draft))
    assert s["markers_left"] is True and s["reviewer_markers"] == ["[REVIEWER: confirm the fee]"] and s["commentary_sentences"]

@pytest.mark.cli
def test_sensitivity_grid_and_reference_table(run_script, make_deal):
    draft = ("The analyst price targets for the Company were as follows:\n| Analyst | Target |\n| A | $30.00 |\n| B | $32.00 |\n\n"
             "Discount rate sensitivity:\n| | 2.0% | 3.0% |\n| 10.0% | $30 | $32 |\n| 11.0% | $28 | $30 |\n")
    s = score(run_script, make_deal(facts={}, book="x", draft=draft, deck={"targets": "reference"}))
    assert s["reference_items_as_tables"] == ["targets"] and s["sensitivity_grids"] == 1

@pytest.mark.cli
def test_defined_term_inconsistency(run_script, make_deal):
    d = make_deal(facts={}, book="x", draft="The Merger Agreement provides... the merger agreement also says... the Merger closes.")
    (d / "defined_terms.json").write_text(json.dumps({"terms": [{"term": "Merger Agreement", "definition": ""}, {"term": "Merger", "definition": ""}]}))
    s = score(run_script, d)
    assert s["glossary_present"] and {"term": "Merger Agreement", "other_form_uses": 1} in s["defined_term_inconsistencies"]

@pytest.mark.cli
def test_empty_draft_exits_cleanly(run_script, make_deal):
    r = run_script("selfscore.py", make_deal(draft="   \n"), "draft/section.txt", check=False)
    assert r.returncode != 0 and "empty draft" in r.stderr and "Traceback" not in r.stderr

@pytest.mark.cli
@pytest.mark.parametrize("book,draft", [("$35.00", "$(35.00)"), ("1,234.5", "$1234.5"), ("12.5%", "12.5x")])
def test_number_forms_that_already_match(run_script, make_deal, book, draft):
    s = score(run_script, make_deal(facts={}, book=f"Offer {book}", draft=f"The price was {draft} in cash."))
    assert s["numbers_not_in_inputs"] == 0

@pytest.mark.cli
@pytest.mark.xfail(strict=True, reason="FINDING: numbers are compared as strings after dropping $ and commas, so a figure written "
                   "with different trailing zeros ($35 in the book, $35.00 in the draft; 12.5% and 12.50%) is reported as not in the inputs.")
@pytest.mark.parametrize("book,draft", [("$35", "$35.00"), ("12.5%", "12.50%")])
def test_same_value_different_trailing_zeros(run_script, make_deal, book, draft):
    s = score(run_script, make_deal(facts={}, book=f"Offer {book}", draft=f"The price was {draft} in cash."))
    assert s["numbers_not_in_inputs"] == 0
