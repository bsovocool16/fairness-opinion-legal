"""precedent_search.find_precedents with EDGAR replaced by fakes: the pool, the window, the regime boost, the cut-off date and
the pruning of section files. No network."""
import pytest
import edgar_precedents as EP
import precedent_search as PS

SEC = {"dcf_only": "Discounted cash flow analysis implied $30.00. " * 200,
       "full": ("Selected public companies analysis implied 9.0x. Discounted cash flow analysis implied $30.00. "
                "Premiums paid analysis implied 30%. ") * 80,
       "short": "Discounted cash flow analysis implied $30.00."}

@pytest.fixture
def fake_edgar(monkeypatch):
    calls = []
    hits = {"A": dict(date="2024-01-01", form="DEFM14A", sec="full", regime_txt=""), "B": dict(date="2025-06-01", form="SC 13E3", sec="full", regime_txt=""),
            "C": dict(date="2025-01-01", form="DEFM14A", sec="dcf_only", regime_txt=""), "D": dict(date="2025-02-01", form="DEFM14A", sec="short", regime_txt=""),
            "LATE": dict(date="2030-01-01", form="DEFM14A", sec="full", regime_txt="")}
    def fts(q, form, start, end, max_pages=10):
        calls.append((q, form, start, end))
        if form != "DEFM14A": return []
        return [{"acc": a, "doc": "d.htm", "form": h["form"], "date": h["date"], "names": [f"Target {a}"], "ciks": [123]} for a, h in hits.items()]
    def best_section(acc, phrases, hint_doc=None):
        return SEC[hits[acc]["sec"]], "d.htm", hits[acc]["form"], hits[acc]["regime_txt"]
    monkeypatch.setattr(EP, "fts", fts); monkeypatch.setattr(PS, "best_section", best_section)
    return calls

def test_ranking_window_and_regime(fake_edgar, tmp_path):
    res = PS.find_precedents("William Blair", ["comps", "dcf", "premiums"], before="2026-01-01", years=6, top=2, out_dir=tmp_path, regime="13e-3", log=lambda m: None)
    accs = [r["acc"] for r in res]
    assert "LATE" not in accs and "D" not in accs                 # after the cut-off; section too short
    assert accs == ["B", "A"]                                      # same coverage; the 13e-3 filing ranks first
    assert res[0]["regime"] == "13e-3" and res[0]["coverage"] == 1.0
    assert sorted(p.stem for p in tmp_path.glob("*.txt")) == ["A", "B"]      # sections outside the top are deleted
    assert {q[2] for q in fake_edgar} == {"2020-01-03"}   # 6 x 365 days back and {q[3] for q in fake_edgar} == {"2026-01-01"}
    assert any(q[0] == '"opinion of William Blair"' for q in fake_edgar)

def test_unknown_bank_searches_its_own_name(fake_edgar):
    assert PS.phrases_for("Ducera Partners") == ["Ducera Partners"]
    assert PS.phrases_for("william blair & company") == ["William Blair"]

def test_thin_pool_adds_the_sign_off_search(fake_edgar):
    PS.find_precedents("Lazard", ["dcf"], before="2026-01-01", top=1, log=lambda m: None)
    assert any(q[0].startswith('"very truly yours"') for q in fake_edgar)
