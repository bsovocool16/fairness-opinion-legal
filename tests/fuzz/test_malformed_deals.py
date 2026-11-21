"""Malformed deal folders: every stage run on the example deal with one input broken. A stage must either succeed or stop with a
non-zero exit, within the time limit, without leaving a half-written JSON output behind. The table of outcomes is also what a
reviewer sees when an input is wrong: as of this suite, a broken JSON input (facts.json, deck_analyses.json, INDEX.json) stops
the stage with a Python traceback rather than a one-line message, which is loud but not friendly."""
import json, shutil, subprocess, sys
import pytest
from conftest import SCRIPTS, fresh_example_deal, script_env

pytestmark = [pytest.mark.fuzz, pytest.mark.cli]

MUTATIONS = {
    "missing": lambda p: p.unlink(),
    "empty": lambda p: p.write_text(""),
    "binary": lambda p: p.write_bytes(bytes(range(256)) * 40),
    "truncated": lambda p: p.write_text(p.read_text(errors="ignore")[: max(1, len(p.read_text(errors="ignore")) // 2)]),
    "json_list": lambda p: p.write_text("[]"),
    "json_nulls": lambda p: p.write_text(json.dumps({k: None for k in json.loads(p.read_text())}) if p.read_text().strip().startswith("{") else "null"),
}
TARGETS = ["facts.json", "deck_analyses.json", "precedents/INDEX.json", "inputs/book.txt", "inputs/opinion_letter.txt", "draft/section.txt"]
STAGES = {"classify_book": ["classify_book.py", "."], "build_shell": ["build_shell.py", "."], "selfscore": ["selfscore.py", ".", "draft/section.txt"], "make_outputs": ["make_outputs.py", "."]}
TEXT_ONLY = {"json_list", "json_nulls"}

CASES = [(s, t, m) for s in STAGES for t in TARGETS for m in MUTATIONS if not (m in TEXT_ONLY and not t.endswith(".json"))]

@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    """One deal with every stage's outputs in place, copied per case, so each stage sees what earlier stages wrote."""
    base = tmp_path_factory.mktemp("malformed"); deal = fresh_example_deal(base / "deal"); home = base / "home"; home.mkdir()
    for argv in STAGES.values():
        subprocess.run([sys.executable, str(SCRIPTS / argv[0]), *argv[1:]], cwd=deal, capture_output=True, env=script_env(home), check=True)
    return deal, home

@pytest.mark.parametrize("stage,target,mutation", CASES, ids=[f"{s}-{t.replace('/', '.')}-{m}" for s, t, m in CASES])
def test_stage_on_broken_input(prepared, tmp_path, stage, target, mutation):
    src, home = prepared; deal = tmp_path / "deal"; shutil.copytree(src, deal)
    MUTATIONS[mutation](deal / target)
    before = {p: p.stat().st_mtime_ns for p in deal.rglob("*.json")}
    r = subprocess.run([sys.executable, str(SCRIPTS / STAGES[stage][0]), *STAGES[stage][1:]], cwd=deal, capture_output=True, text=True, env=script_env(home), timeout=120)
    for p in deal.rglob("*.json"):
        if p.stat().st_mtime_ns != before.get(p) and p.name != "INDEX.json":
            json.loads(p.read_text())                        # anything the stage wrote is complete JSON
    if r.returncode != 0:
        assert r.stderr.strip(), "failed without saying why"
