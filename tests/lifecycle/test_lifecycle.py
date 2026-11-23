"""Offline tests for the ticker-to-proxy lifecycle (no network): the full chain on the synthetic fixture, the drafting-convention
checker against deliberately broken models, the letter's refusal below the valuation ranges, and the XBRL helpers on hand-built
company facts. Needs LibreOffice for the recalculation. Run: python3 -m pytest tests/lifecycle -q"""
import sys, json, shutil, subprocess, copy
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[2]; PLUGIN = ROOT / "fairness-opinion-legal"; LC = PLUGIN / "scripts" / "lifecycle"
FIXTURE = PLUGIN / "examples" / "lifecycle-fixture" / "company.json"
sys.path.insert(0, str(LC))
_lo = bool(shutil.which("soffice") or shutil.which("libreoffice")) or Path("/Applications/LibreOffice.app/Contents/MacOS/soffice").exists()
needs_lo = pytest.mark.skipif(not _lo, reason="LibreOffice needed to recalculate the model")

def chain(deal, *extra):
    return subprocess.run([sys.executable, str(LC / "ticker_to_proxy.py"), "run", "EXMP", str(deal), "--advisor", "Evercore Group L.L.C.", "--fixture", str(FIXTURE), "--opinion-date", "2026-11-20", *extra],
                          capture_output=True, text=True, timeout=600)

@pytest.fixture(scope="module")
def deal(tmp_path_factory):
    d = tmp_path_factory.mktemp("deal"); r = chain(d)
    assert r.returncode == 0, r.stdout + r.stderr
    return d

@needs_lo
def test_every_stage_ok(deal):
    m = json.load(open(deal / "lifecycle" / "manifest.json"))["stages"]
    assert [s for s, v in m.items() if v["status"] == "ok"] == ["fetch", "terms", "model", "check", "deck", "letter", "handoff"]

@needs_lo
def test_model_conventions_and_values(deal):
    import check_model
    assert check_model.check(deal / "lifecycle" / "model.xlsx", deal / "lifecycle" / "model_values.xlsx") == []
    v = json.load(open(deal / "lifecycle" / "valuation.json"))
    assert v["errors"] == []
    for k, r in v["ranges"].items(): assert 0 < r["low"] <= r["high"], k
    c = v["cells"]
    assert abs(c["sens_pgr_mid"]["value"] - c["dcf_ps_mid_perp"]["value"]) < 1e-6      # the sensitivity grid's center ties to the DCF tab
    assert abs(c["sens_exit_mid"]["value"] - c["dcf_ps_mid_exit"]["value"]) < 1e-6
    assert 0.05 < c["wacc"]["value"] < 0.15

@needs_lo
def test_book_numbers_match_model(deal):
    v = json.load(open(deal / "lifecycle" / "valuation.json")); text = (deal / "inputs" / "book.txt").read_text()
    for k in ("comps", "dcf_pgr", "dcf_exit", "lbo"):
        for end in ("low", "high"): assert f"${v['ranges'][k][end]:,.2f}" in text, (k, end)

@needs_lo
def test_handoff_matches_pipeline_intake(deal):
    f = json.load(open(deal / "facts.json"))
    for key in ("advisor", "addressee", "opinion_date", "target", "ticker", "buyer", "buyer_type", "consideration", "offer_price", "regime"): assert f.get(key) not in (None, ""), key
    da = json.load(open(deal / "deck_analyses.json"))["deck_analyses"]
    assert {"dcf", "comps", "lbo", "premiums"} <= {k for k, s in da.items() if s == "core"}
    assert "precedents" not in da and "targets" not in da      # the book must not claim analyses it does not contain
    assert (deal / "inputs" / "opinion_letter.txt").read_text().count("fair, from a financial point of view") == 1

@needs_lo
def test_checker_catches_broken_models(deal, tmp_path):
    import check_model
    from openpyxl import load_workbook
    from openpyxl.styles import Font
    src = deal / "lifecycle" / "model.xlsx"
    def broken(mutate):
        wb = load_workbook(src); mutate(wb); p = tmp_path / "m.xlsx"; wb.save(p); return {r for r, _, _ in check_model.check(p)}
    def hardcode(wb):
        ws = wb["DCF"]
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("=") and "Assumptions!" in c.value: c.value = c.value + "*1.05"; return
    assert "C2" in broken(hardcode)
    def blue_formula(wb):
        c = wb["DCF"]["E6"]; c.font = Font(color="0000FF")
    assert "C1" in broken(blue_formula)
    def typed_in_calc(wb): wb["DCF"]["E6"] = 123.4
    assert {"C1", "C3"} & broken(typed_in_calc)
    def orphan(wb): wb["Assumptions"]["C200"] = 0.07; wb["Assumptions"]["C200"].font = Font(color="0000FF")
    assert "C6" in broken(orphan)

@needs_lo
def test_letter_refuses_low_offer(tmp_path):
    r = chain(tmp_path / "low", "--premium", "-0.10")
    assert r.returncode == 2 and "STOPPED at letter" in r.stdout
    meta = json.load(open(tmp_path / "low" / "lifecycle" / "letter.json")); assert meta["written"] is False and not meta["supported"]

def test_xbrl_ltm_and_annual():
    import fetch_company as F
    def e(s, en, v, form="10-K", filed="2026-01-01"): return {"start": s, "end": en, "val": v, "form": form, "filed": filed, "accn": "x"}
    facts = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [e("2024-01-01", "2024-12-31", 100e6), e("2025-01-01", "2025-12-31", 120e6),
             e("2025-01-01", "2025-06-30", 55e6, "10-Q"), e("2026-01-01", "2026-06-30", 70e6, "10-Q")]}}},
             "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [{"end": "2026-07-20", "val": 10e6, "accn": "a", "filed": "2026-08-01", "form": "10-Q"}]}}}}}
    s = F.duration_series(facts, F.TAGS["revenue"])
    assert sorted(F.annual(s)) == ["2024-12-31", "2025-12-31"]
    v, meta = F.ltm(s); assert abs(v - 135e6) < 1 and meta["basis"] == "LTM"      # 120 + 70 - 55
    assert F.shares_out(facts)[0] == 10.0

def test_sanity_flags_peer_mismatch_and_thin_sets():
    import build_model
    def cells(**kw): return {k: {"value": v, "cell": "X!A1"} for k, v in kw.items()}
    rng = {f"ff_{k}_{e}": v for k in ("trading_range", "premiums", "comps", "dcf_pgr", "dcf_exit", "lbo") for e, v in (("lo", 180.0), ("hi", 220.0))}
    # a premium-multiple company valued off cheaper peers (the live WTS case): both warnings fire
    F = build_model.sanity(cells(wacc=0.09, tgt_ev_ltm_ebitda_unaff=17.7, comps_q1_ebitda=10.3, comps_q3_ebitda=14.0, px_unaff=356.67, comps_table=[["A"], ["B"], ["C"], ["D"]], **rng))
    assert any("interquartile" in f for f in F) and any("more than 30%" in f for f in F)
    # two peers (the live DSGR case)
    F = build_model.sanity(cells(wacc=0.09, tgt_ev_ltm_ebitda_unaff=12.0, comps_q1_ebitda=10.0, comps_q3_ebitda=13.0, px_unaff=200.0, comps_table=[["A"], ["B"]], **rng))
    assert any("only 2 peer" in f for f in F) and not any("interquartile" in f for f in F)

@needs_lo
def test_reverse_dcf_and_ltm_anchor(deal):
    v = json.load(open(deal / "lifecycle" / "valuation.json")); c = {k: x["value"] for k, x in v["cells"].items()}
    g, w = c["rdcf_g"], c["wacc_dcf_perp"]
    # the implied growth rate reproduces the terminal value the unaffected price requires, on the same final-year cash flow
    assert abs(c["rdcf_tv"] * (w - g) - c["ufcf_N"] * (1 + g)) < 1e-6 * c["rdcf_tv"]
    assert abs(c["rdcf_x"] * c["ebitda_N"] - c["rdcf_tv"]) < 1e-6 * c["rdcf_tv"]
    # the fixture carries LTM figures to 2026-09-30, so year one is anchored on them
    assert v["assumption_basis"]["growth"].startswith("year 1: LTM revenue to 2026-09-30")
