"""Golden snapshots: every deterministic stage run in order on the bundled example deal (Distribution Solutions Group 2026,
William Blair, Rule 13e-3), each output compared with tests/golden/expected/<stage>/. A difference fails with a unified diff;
when the change is intended, `make golden-update` (pytest --update-goldens) rewrites the expected files for review in git."""
import difflib, json, subprocess, sys
from pathlib import Path
import pytest
from conftest import GOLDEN, SCRIPTS, EXAMPLE_RUN, fresh_example_deal, script_env
from stages import STAGES

pytestmark = pytest.mark.golden

@pytest.fixture(scope="module")
def pipeline(tmp_path_factory):
    """Runs every stage once, in order, in one deal folder; returns {stage name: {snapshot name: text}}."""
    base = tmp_path_factory.mktemp("golden"); deal = fresh_example_deal(base / "deal"); home = base / "home"; home.mkdir()
    snaps = {}
    for st in STAGES:
        if st.fn: snaps[st.name] = st.fn(deal); continue
        r = subprocess.run([sys.executable, str(SCRIPTS / st.argv[0]), *st.argv[1:]], cwd=deal, capture_output=True, text=True, env=script_env(home), timeout=600)
        assert r.returncode == 0, f"stage {st.name} failed:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}"
        out = {o.replace("/", "__"): (deal / o).read_text() for o in st.outputs}
        if st.stdout: out["stdout.txt"] = r.stdout
        snaps[st.name] = out
    return snaps

def canon(name, text):
    """JSON compared as data with key order kept (order is part of the output), text exactly."""
    if name.endswith(".json"):
        return json.dumps(json.loads(text), indent=1, ensure_ascii=False) + "\n"
    return text

@pytest.mark.parametrize("stage", [s.name for s in STAGES])
def test_stage_matches_golden(stage, pipeline, request):
    update = request.config.getoption("--update-goldens"); got = pipeline[stage]; d = GOLDEN / stage
    if update:
        d.mkdir(parents=True, exist_ok=True)
        for old in d.glob("*"): old.unlink()
        for name, text in got.items(): (d / name).write_text(canon(name, text))
        pytest.skip(f"golden updated: {d}")
    assert d.exists(), f"no golden for stage {stage}; run make golden-update and review the files"
    want_names = sorted(p.name for p in d.glob("*")); assert sorted(got) == want_names, f"{stage} writes {sorted(got)}, golden has {want_names}"
    for name, text in got.items():
        a, b = (d / name).read_text(), canon(name, text)
        if a != b:
            diff = "".join(list(difflib.unified_diff(a.splitlines(True), b.splitlines(True), f"golden/{stage}/{name}", f"now/{stage}/{name}", n=2))[:200])
            pytest.fail(f"{stage}/{name} differs from the golden (if intended: make golden-update)\n{diff}")

def test_shell_matches_committed_example_run(pipeline):
    """The shell rebuilt by today's code is the shell the bundled run shipped with: the demo replays what the code makes."""
    for name in ("shell_composite.txt", "shell_composite_eligible.txt", "shell_suggested.txt"):
        assert pipeline["build_shell"][f"shell__{name}"] == (EXAMPLE_RUN / "shell" / name).read_text(), name

def test_demo_walk_replays_every_stage(run_script):
    r = run_script("demo.py", "walk", EXAMPLE_RUN, "--stage", "all")
    for word in ("intake", "search", "shell", "draft", "redline"):
        assert word.lower() in r.stdout.lower()
    assert "Traceback" not in r.stderr
