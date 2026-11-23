"""Held-out backtest harness (scripts/backtest): record parsers, point-in-time fetch filters, leakage audit, scoring math.
No network: every parser runs on short excerpts written in the shape EDGAR's html_to_text produces."""
import json, sys
from pathlib import Path
import pytest
from conftest import SCRIPTS
for p in (SCRIPTS / "backtest", SCRIPTS / "lifecycle"):
    if str(p) not in sys.path: sys.path.insert(0, str(p))
import record as R, score as S, backtest as BT, fetch_company as FC

SECTION = """Opinion of Example Bank LLC to the Special Committee
Selected Public Companies Analysis
Example Bank reviewed the selected companies listed below.
The Selected Companies considered by Example Bank were:
| Selected Companies | Enterprise Value / 2027E Adjusted EBITDA |
| Alpha Foods, Inc. | 7.3x |
| The Beta Company | 9.2x |
Example Bank noted that the low, high and median multiples for the Selected Companies were 7.3x, 9.2x, and 8.2x, respectively. Example Bank applied the multiple range of 6.6x to 8.6x to the Company's 2027E Adjusted EBITDA. This analysis indicated an approximate implied per share equity value reference range, rounded to the nearest $0.05, of $5.70 to $9.00, as compared to the consideration of $14.25.
Discounted Cash Flow Analysis
Example Bank applied perpetuity growth rates of 1.5% to 2.5% and discount rates of 7.9% to 8.5%. This analysis indicated an approximate implied per share equity value reference range of $10.60 to $14.80.
Historical Trading Prices
Example Bank noted that the low and high intra-day prices were as follows:
| Subject | Low | High |
| Class A Common Stock | $6.78 | $14.67 |
All-Cash Premia
Application of a range of premia of 30% to 50% to the closing price would indicate an illustrative potential range of prices, rounded to the nearest $0.05, of $9.35 to $10.80.
Equity Research
The range of undiscounted price targets was $8.00 per share to $15.00 per share, for reference only.
"""

PROXY = """Summary of the Projections
The following table presents a summary of the Projections:
| ($ in millions) | Q2- Q42026E | 2027E | 2028E | 2029E |
| Net Sales | $1,123 | $1,541 | $1,609 | $1,673 |
| Adjusted EBITDA (1)(2) | $180 | $246 | $263 | $283 |
(2) Last Twelve Months Adjusted EBITDA for the period ended March 29, 2026 was $219.
Summary Consolidated Statements of Operations and Comprehensive Income (Loss)
| (Audited) Fiscal Years Ended December 28, 2025 | December 29, 2024 | (in millions) |
| Net Sales | $1,438.8 | $1,409.2 |
| Income from operations | $19.5 | $58.9 |
| Net income (loss) | $(7.7) | $30.7 |
| Net income (loss) attributable to controlling interest | $0.8 | $15.9 |
Annex A- 40
Table of Contents
July 20, 2026
Special Committee of the Board of Directors
You have requested our opinion. The consideration is fair, from a financial point of view, to such holders.
Very truly yours,
EXAMPLE BANK LLC
/s/ Example Bank LLC
Annex B- 4
Table of Contents
Annex C
"""

def test_section_parse_ranges_params_peers():
    t = R.parse_section(SECTION); A = t["analyses"]
    assert (A["comps"]["range"]["low"], A["comps"]["range"]["high"]) == (5.70, 9.00)   # the "nearest $0.05" is not read as a bound
    assert A["comps"]["peers"] == ["Alpha Foods, Inc.", "The Beta Company"]           # the header row is not a peer
    assert A["comps"]["params"]["multiple_applied"] == [6.6, 8.6] and A["comps"]["params"]["peer_low_high_median"] == [7.3, 9.2, 8.2]
    assert A["dcf"]["params"] == {"discount_rate": [0.079, 0.085], "perpetuity_growth": [0.015, 0.025]} and A["dcf"]["method"] == "pgr"
    assert (A["trading_range"]["range"]["low"], A["trading_range"]["range"]["high"]) == (6.78, 14.67)
    assert A["premiums"]["params"]["premium"] == [0.30, 0.50] and A["premiums"]["range"]["low"] == 9.35
    assert A["targets"]["range"]["high"] == 15.0 and A["targets"]["reference_only"]

def test_projections_historicals_letter():
    pj = R.projections(PROXY)
    assert pj["years"] == ["stub 2026", "2027", "2028", "2029"] and pj["rows"]["Adjusted EBITDA"] == [180, 246, 263, 283] and pj["ltm_adj_ebitda"] == 219
    h = R.historicals(PROXY)
    assert h[2025] == {"revenue": 1438.8, "ebit": 19.5, "net_income": -7.7, "net_income_parent": 0.8}
    lt = R.letter(PROXY, ["Example Bank"])
    assert lt.startswith("July 20, 2026") and lt.rstrip().endswith("/s/ Example Bank LLC") and "Annex" not in lt

def test_point_in_time_drops_later_filings():
    facts = {"cik": 1, "facts": {"us-gaap": {"Revenues": {"units": {"USD": [{"end": "2025-12-31", "val": 1, "filed": "2026-02-20"}, {"end": "2025-12-31", "val": 2, "filed": "2026-08-01"}]}},
                                             "Later": {"units": {"USD": [{"end": "2026-06-30", "val": 3, "filed": "2026-08-01"}]}}}}}
    pit = FC.point_in_time(facts, "2026-07-20")
    assert [e["val"] for e in pit["facts"]["us-gaap"]["Revenues"]["units"]["USD"]] == [1] and "Later" not in pit["facts"]["us-gaap"]
    assert FC.point_in_time(facts, None) is facts

def test_name_as_of_and_history_window():
    sub = {"name": "NEW ROYAL HOLDCO I INC.", "formerNames": [{"name": "GOLDEN ENTERTAINMENT, INC.", "from": "2015-07-31T00:00:00.000Z", "to": "2026-04-30T00:00:00.000Z"}]}
    assert FC.name_as_of(sub, "2025-11-01") == "GOLDEN ENTERTAINMENT, INC." and FC.name_as_of(sub, "2026-06-01") == "NEW ROYAL HOLDCO I INC."
    assert FC.years_back(None) == 2 and FC.years_back("2000-01-01") > 20

def test_cached_chart(tmp_path, monkeypatch):
    (tmp_path / "yahoo_ABC.json").write_text(json.dumps({"chart": {"result": [{"timestamp": [1784553000], "indicators": {"quote": [{"close": [7.45]}]}}]}}))
    monkeypatch.setenv("PRICE_CACHE", str(tmp_path))
    assert FC.yahoo_closes("ABC")[0][1] == 7.45

def test_range_metrics():
    assert S.iou((1, 3), (2, 4)) == round(1 / 3, 4) and S.iou((1, 2), (3, 4)) == 0 and S.iou((1, 2), (1, 2)) == 1
    assert [S.side(5, (6, 7)), S.side(6.5, (6, 7)), S.side(8, (6, 7))] == ["below", "within", "above"]
    assert S.jaccard(["The Marzetti Company", "B&G Foods, Inc."], ["MARZETTI CO", "B&G FOODS INC", "Post Holdings, Inc."]) == round(2 / 3, 4)

def _blind(tmp_path, filed="2026-05-06", hist_end="2026-07-20", precedent_date="2025-01-01", acc="0000000000-26-000001"):
    lc = tmp_path / "blind" / "lifecycle"; lc.mkdir(parents=True)
    co = {"as_of": "2026-07-20", "target": {"ticker": "ABC", "annual": [{"sources": {"revenue": {"filed": filed}}}], "price": {"date": "2026-07-20", "history_1y": [["2026-07-20", 7.45]]}},
          "peers": [{"ticker": "XYZ", "price": {"date": hist_end, "history_1y": [[hist_end, 10]]}}], "market": {"risk_free": {"date": "2026-07-20"}}}
    (lc / "company.json").write_text(json.dumps(co))
    (lc / "deal_terms.json").write_text(json.dumps({"unaffected_date": "2026-07-20"}))
    (tmp_path / "blind" / "precedents").mkdir()
    (tmp_path / "blind" / "precedents" / "results.json").write_text(json.dumps([{"acc": acc, "date": precedent_date}]))
    return {"cutoff": "2026-07-20", "opinion_date": "2026-07-20", "unaffected_date": "2026-07-20", "record": {"proxy": {"acc": "0001193125-26-411198"}},
            "announced": "2026-07-21", "drafter_training_cutoff": "2026-06-30"}

def test_audit_passes_clean_run(tmp_path):
    r = BT.audit(_blind(tmp_path), tmp_path)
    assert r["passed"], r["failures"]

@pytest.mark.parametrize("kw,needle", [({"filed": "2026-08-01"}, "filed 2026-08-01"), ({"hist_end": "2026-07-21"}, "price history"),
                                       ({"precedent_date": "2026-08-24"}, "not before the opinion"), ({"acc": "0001193125-26-411198"}, "deal's own filing")])
def test_audit_catches_leaks(tmp_path, kw, needle):
    r = BT.audit(_blind(tmp_path, **kw), tmp_path)
    assert not r["passed"] and any(needle in f for f in r["failures"]), r["failures"]

def test_audit_warns_on_memorization_risk(tmp_path):
    spec = _blind(tmp_path); spec["announced"] = "2026-03-01"
    assert any("training cutoff" in w for w in BT.audit(spec, tmp_path)["warnings"])

def test_spec_rejects_cutoff_after_opinion(tmp_path):
    p = tmp_path / "s.json"; base = json.loads((SCRIPTS.parent / "examples" / "backtest" / "utz.json").read_text())
    base["cutoff"] = "2026-07-22"; p.write_text(json.dumps(base))
    with pytest.raises(SystemExit): BT.load_spec(p)
    assert BT.load_spec(SCRIPTS.parent / "examples" / "backtest" / "utz.json")["cik"] == 1739566

def test_bundled_price_cache_stops_at_cutoff():
    import datetime
    j = json.loads((SCRIPTS.parent / "examples" / "backtest" / "utz-prices" / "yahoo_UTZ.json").read_text())
    last = datetime.datetime.fromtimestamp(j["chart"]["result"][0]["timestamp"][-1], datetime.timezone.utc).date().isoformat()
    assert last <= "2026-07-20"
