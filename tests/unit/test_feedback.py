"""feedback.py: reviewer notes, their scopes and the CLI round trip (always against a scratch file, never the user's)."""
import json
import pytest
import feedback as FB

def entry(scope="all", stage="all"): return {"id": "abc123", "date": "2026-01-01", "stage": stage, "scope": scope, "note": "n."}

@pytest.mark.parametrize("scope,advisor,code,want", [
    ("all", "", "", True), ("advisor:William Blair", "William Blair & Company L.L.C.", "x", True), ("advisor:Goldman Sachs", "William Blair", "x", False),
    ("advisor:William Blair", "", "x", False), ("deal:DSGR-2026", "", "dsgr-2026", True), ("deal:DSGR-2026", "", "other", False), ("bogus", "a", "b", False)])
def test_applies_scope(scope, advisor, code, want):
    assert FB.applies(entry(scope), advisor, code, None) is want

def test_applies_stage():
    assert FB.applies(entry(stage="draft"), "", "", "draft") and FB.applies(entry(stage="all"), "", "", "shell")
    assert not FB.applies(entry(stage="draft"), "", "", "shell")

def test_line_round_trip(tmp_path):
    p = tmp_path / "f.md"; p.write_text(FB.HEADER + FB.line_of(entry("advisor:Lazard", "draft")) + "\n")
    [e] = FB.parse(p); assert (e["scope"], e["stage"], e["note"]) == ("advisor:Lazard", "draft", "n.")

def test_deal_file_default_scope(tmp_path):
    p = tmp_path / "f.md"; p.write_text(FB.line_of(entry()) + "\n")
    assert FB.parse(p, default_scope="deal:x")[0]["scope"] == "deal:x"

@pytest.mark.cli
def test_cli_add_for_remove(run_script, make_deal, tmp_path):
    f = tmp_path / "notes.md"; d = make_deal(facts={"advisor": "William Blair & Company L.L.C."})
    r = run_script("feedback.py", "--file", f, "add", "Use the full legal name of every peer", "--scope", "advisor:William Blair", "--stage", "draft", "--date", "2026-11-01")
    nid = r.stdout.split("[", 1)[1][:6]
    assert "Use the full legal name of every peer." in f.read_text()
    assert nid in run_script("feedback.py", "--file", f, "for", d, "--stage", "draft").stdout
    assert "No feedback notes apply" in run_script("feedback.py", "--file", f, "for", d, "--stage", "shell").stdout
    run_script("feedback.py", "--file", f, "remove", nid)
    assert nid not in f.read_text()
    bad = run_script("feedback.py", "--file", f, "add", "x", "--scope", "everyone", check=False)
    assert bad.returncode != 0 and "--scope must be" in bad.stderr
