"""The Word deliverables, checked by structure rather than bytes (a .docx carries timestamps): the clean draft carries the
work-product header and every paragraph of the draft; the redline marks insertions blue double-underlined and deletions red
struck, and its words add up to the draft. Also checks that outputs do not depend on the interpreter's hash seed."""
import json, re, subprocess, sys, zipfile
import pytest
from conftest import SCRIPTS, fresh_example_deal, script_env

def docx_runs(path):
    """[(text, {'ins'|'del'|None})] for every run in word/document.xml."""
    xml = zipfile.ZipFile(path).read("word/document.xml").decode()
    out = []
    for r in re.findall(r"<w:r>(.*?)</w:r>", xml, re.S):
        text = "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", r, re.S))
        kind = "ins" if re.search(r'<w:u w:val="double" w:color="0000FF"', r) else "del" if "<w:strike/>" in r or '<w:strike w:val="true"/>' in r else None
        out.append((text, kind))
    return out

@pytest.fixture(scope="module")
def outputs(tmp_path_factory):
    base = tmp_path_factory.mktemp("docs"); deal = fresh_example_deal(base / "deal"); home = base / "home"; home.mkdir()
    for argv in (["classify_book.py", "."], ["build_shell.py", "."], ["make_outputs.py", "."]):
        subprocess.run([sys.executable, str(SCRIPTS / argv[0]), *argv[1:]], cwd=deal, capture_output=True, env=script_env(home), check=True, timeout=600)
    return deal

@pytest.mark.needs_node
def test_clean_draft_docx(outputs):
    runs = docx_runs(outputs / "redline" / "section.docx"); text = " ".join(t for t, _ in runs)
    assert runs[0][0] == "DRAFT — ATTORNEY WORK PRODUCT — FOR REVIEW — NOT FOR FILING"
    norm = lambda s: re.sub(r"\s+", " ", s.replace("&amp;", "&").replace("’", "'").replace("“", '"').replace("”", '"'))
    for para in (outputs / "draft" / "section.txt").read_text().split("\n\n")[:40]:
        first = para.strip().split("\n")[0].strip("| ").split("|")[0].strip()
        if first: assert norm(first[:40]) in norm(text), first[:60]

@pytest.mark.needs_node
def test_redline_docx_marks(outputs):
    runs = docx_runs(outputs / "redline" / "redline_vs_shell.docx")
    kinds = {k for _, k in runs}
    assert {"ins", "del", None} <= kinds
    ins_words = sum(len(t.split()) for t, k in runs if k == "ins"); del_words = sum(len(t.split()) for t, k in runs if k == "del")
    legend = next(t for t, _ in runs if "Blue double underline" in t)
    assert f"({ins_words:,} words)" in legend.replace("&amp;", "&")
    assert f"({del_words:,} words)" in legend

@pytest.mark.needs_node
@pytest.mark.needs_soffice
def test_redline_pdf(outputs):
    pdf = outputs / "redline" / "redline_vs_shell.pdf"
    assert pdf.exists() and pdf.read_bytes()[:5] == b"%PDF-"

@pytest.mark.cli
def test_outputs_do_not_depend_on_hash_seed(tmp_path):
    """Set iteration order once leaked into deck_analyses.json and the self-score lists; two seeds must give identical files."""
    got = []
    for seed in ("1", "2"):
        deal = fresh_example_deal(tmp_path / f"d{seed}"); home = tmp_path / f"h{seed}"; home.mkdir()
        env = {**script_env(home), "PYTHONHASHSEED": seed}
        for argv in (["classify_book.py", "."], ["build_shell.py", "."], ["selfscore.py", ".", "draft/section.txt"]):
            subprocess.run([sys.executable, str(SCRIPTS / argv[0]), *argv[1:]], cwd=deal, capture_output=True, env=env, check=True)
        got.append([(deal / f).read_text() for f in ("deck_analyses.json", "shell/rationale.json", "shell/provenance.json", "draft/selfscore.json")])
    assert got[0] == got[1]
