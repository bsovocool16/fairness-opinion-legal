"""make_outputs.blocks_of (the clean draft's structure), defined_terms.glossary, classify_book.classify."""
import pytest
import classify_book as CB
import defined_terms as DT
import make_outputs as MO

def test_blocks_of():
    b = MO.blocks_of("Opinion of Acme\n\nAcme delivered its opinion, dated May 1, 2026.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n• a bullet item")
    assert [x["type"] for x in b] == ["h", "p", "table", "p"]
    assert b[2]["rows"] == [["A", "B"], ["1", "2"]]

def test_header_default_without_profile(monkeypatch, tmp_path):
    monkeypatch.setattr(MO, "PROFILE", tmp_path / "missing.md")
    assert MO.header() == "DRAFT — ATTORNEY WORK PRODUCT — FOR REVIEW — NOT FOR FILING"

def test_header_from_profile(monkeypatch, tmp_path):
    p = tmp_path / "CLAUDE.md"; p.write_text('- Work-product header on every document: [DEFAULT: "PRIVILEGED DRAFT"]\n')
    monkeypatch.setattr(MO, "PROFILE", p); assert MO.header() == "PRIVILEGED DRAFT"

def test_glossary():
    raw = DT.clean('Acme Corporation (the “Company”), Parent LLC (“Parent”) and the Agreement and Plan of Merger (as amended, the "Merger Agreement"). '
                   "The Company (the “Company”) again. A note (see page 4).")
    g = DT.glossary(raw)
    assert [t["term"] for t in g] == ["Company", "Parent", "Merger Agreement"]
    assert "Acme Corporation" in g[0]["definition"]

def test_glossary_cp1252_quotes():
    assert [t["term"] for t in DT.glossary(DT.clean("Foo Inc. (the \x93Buyer\x94)."))] == ["Buyer"]

def test_classify_pages_and_status():
    book = ("Selected Public Companies\n8.0x 10.0x\n-----PAGE-----\nDiscounted Cash Flow Analysis\n$30.00\n-----PAGE-----\n"
            "Analyst Price Targets\n$33.00\n-----PAGE-----\nLBO Analysis\nfor reference only\n20%\n-----PAGE-----\nDCF Sensitivity\n10% 11%")
    c = CB.classify(book)
    assert c["comps"]["status"] == "core" and c["comps"]["pages"] == [1]
    assert c["targets"]["status"] == "reference" and c["lbo"]["status"] == "reference" and c["sensitivity"]["status"] == "grid"
    assert 2 in c["dcf"]["pages"]

def test_classify_needs_numbers_for_a_body_hit():
    assert "dcf" not in CB.classify("Overview\nAgenda\nTimeline\nWe may later run a discounted cash flow analysis.")

@pytest.mark.cli
def test_classify_cli_without_book(run_script, make_deal):
    r = run_script("classify_book.py", make_deal(), check=False)
    assert r.returncode != 0 and "no inputs/book.txt" in r.stderr
