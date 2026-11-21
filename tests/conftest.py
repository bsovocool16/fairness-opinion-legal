"""Shared fixtures for the suite.

Layout: tests/unit (one file per script, plain examples), tests/fuzz (Hypothesis properties and malformed inputs),
tests/golden (every pipeline stage run on the bundled example deal and compared with tests/golden/expected).
Stages are declared once in tests/stages.py; a new stage of the pipeline is one entry there."""
import json, os, shutil, subprocess, sys
from pathlib import Path
import pytest
from hypothesis import HealthCheck, settings

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "fairness-opinion-legal"
SCRIPTS = PLUGIN / "scripts"
EXAMPLE_RUN = PLUGIN / "examples" / "distribution-solutions-2026" / "run"
GOLDEN = Path(__file__).resolve().parent / "golden" / "expected"
for p in (SCRIPTS, SCRIPTS / "redline", Path(__file__).resolve().parent):
    if str(p) not in sys.path: sys.path.insert(0, str(p))

# Hypothesis depth: "dev" for a quick local pass, "ci" (default) fixed-seed so CI is reproducible, "deep" for a long hunt.
settings.register_profile("dev", max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])
settings.register_profile("ci", max_examples=150, deadline=None, derandomize=True, suppress_health_check=[HealthCheck.too_slow])
settings.register_profile("deep", max_examples=3000, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large])
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "ci"))

HAS_NODE = bool(shutil.which("node")) and (SCRIPTS / "redline" / "node_modules" / "docx").exists()
HAS_SOFFICE = bool(shutil.which("soffice")) or Path("/Applications/LibreOffice.app/Contents/MacOS/soffice").exists()

def pytest_addoption(parser):
    parser.addoption("--update-goldens", action="store_true", help="rewrite tests/golden/expected from the current code instead of comparing")

def pytest_collection_modifyitems(config, items):
    for item in items:
        if "needs_node" in item.keywords and not HAS_NODE:
            item.add_marker(pytest.mark.skip(reason="node + docx package missing (npm ci in fairness-opinion-legal/scripts/redline)"))
        if "needs_soffice" in item.keywords and not HAS_SOFFICE:
            item.add_marker(pytest.mark.skip(reason="LibreOffice missing"))

def script_env(home):
    """A clean environment: HOME points at a scratch folder so the user's real practice profile and feedback notes are never
    read or written, a fixed hash seed so set order cannot leak into outputs, and no EDGAR identity (no network)."""
    env = {k: v for k, v in os.environ.items() if k not in ("EDGAR_UA",)}
    env.update(HOME=str(home), PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1")
    return env

@pytest.fixture
def run_script(tmp_path):
    """run_script("build_shell.py", deal, check=True) -> CompletedProcess. Scripts run exactly as the skills call them."""
    home = tmp_path / "home"; home.mkdir(exist_ok=True)
    def _run(name, *args, check=True, cwd=None, timeout=300, env=None):
        r = subprocess.run([sys.executable, str(SCRIPTS / name), *map(str, args)], capture_output=True, text=True, cwd=cwd, timeout=timeout, env=env or script_env(home))
        if check and r.returncode != 0:
            raise AssertionError(f"{name} {' '.join(map(str, args))} exited {r.returncode}\nstdout:\n{r.stdout[-3000:]}\nstderr:\n{r.stderr[-3000:]}")
        return r
    return _run

@pytest.fixture
def example_deal(tmp_path):
    """A fresh copy of the bundled example deal's inputs, with every derived file removed so each stage rebuilds it."""
    return fresh_example_deal(tmp_path / "deal")

def fresh_example_deal(dst):
    shutil.copytree(EXAMPLE_RUN, dst)
    for rel in ("deck_analyses.json", "shell", "redline", "filed", "draft/selfscore.json"):
        p = dst / rel
        if p.is_dir(): shutil.rmtree(p)
        elif p.exists(): p.unlink()
    return dst

@pytest.fixture
def make_deal(tmp_path):
    """make_deal(facts=..., book=..., precedents={id: text}, index=[...], deck=..., draft=...) -> a minimal synthetic deal folder."""
    def _make(name="deal", facts=None, book=None, ocr=None, letter=None, precedents=None, index=None, deck=None, draft=None):
        d = tmp_path / name; (d / "inputs").mkdir(parents=True, exist_ok=True); (d / "precedents").mkdir(exist_ok=True)
        if facts is not None: (d / "facts.json").write_text(facts if isinstance(facts, str) else json.dumps(facts))
        if book is not None: (d / "inputs" / "book.txt").write_text(book)
        if ocr is not None: (d / "inputs" / "book_ocr.txt").write_text(ocr)
        if letter is not None: (d / "inputs" / "opinion_letter.txt").write_text(letter)
        for k, v in (precedents or {}).items(): (d / "precedents" / f"{k}.txt").write_text(v)
        if index is not None: (d / "precedents" / "INDEX.json").write_text(index if isinstance(index, str) else json.dumps(index))
        if deck is not None: (d / "deck_analyses.json").write_text(deck if isinstance(deck, str) else json.dumps({"deck_analyses": deck}))
        if draft is not None: (d / "draft").mkdir(exist_ok=True); (d / "draft" / "section.txt").write_text(draft)
        return d
    return _make
