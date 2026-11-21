#!/usr/bin/env python3
"""Stage 1 of the ticker-to-proxy lifecycle: public data for a ticker and its peers, written as company.json (schema company/1).

  python3 fetch_company.py <TICKER> <out dir> [--peers A,B,C] [--max-peers 6] [--as-of YYYY-MM-DD]

Sources, all public and keyless:
  SEC company_tickers.json            ticker -> CIK
  SEC submissions/CIK##########.json  legal name, SIC code, exchange, fiscal year end
  SEC XBRL companyfacts               annual and LTM revenue, EBIT, D&A, capex, interest, taxes, NWC; latest cash, debt, NCI, shares
  SEC EDGAR company browse by SIC     peer candidates (same SIC, has a ticker, revenue within 0.2x-5x), unless --peers is given
  Yahoo Finance chart API, Stooq CSV  daily closes, two years, for the price, the 52-week range and 2-year weekly beta vs the S&P 500
  FRED DGS10                          10-year Treasury yield, the risk-free rate

Every number carries its source (tag, form, period, filed date) so the model's Historicals tab can show it. A field that cannot
be found is null with a note; later stages flag it rather than guess. EDGAR requests send the profile's SEC contact identity."""
import sys, re, math, argparse, datetime, statistics, io, csv
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import sec_json, get, save, SCHEMAS, mm, sec_ua

TAGS = {  # priority order; the series is merged across tags by period, earlier tags winning
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet", "SalesRevenueGoodsNet", "RevenuesNetOfInterestExpense"],
    "ebit": ["OperatingIncomeLoss"],
    "da": ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization", "DepreciationAmortizationAndAccretionNet", "Depreciation"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets", "PaymentsForCapitalImprovements"],
    "interest": ["InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt", "InterestPaidNet"],
    "pretax": ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest", "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"],
    "tax": ["IncomeTaxExpenseBenefit"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "sbc": ["ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"],
}
INSTANT = {
    "cash": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", "Cash"],
    "st_investments": ["ShortTermInvestments", "MarketableSecuritiesCurrent", "AvailableForSaleSecuritiesDebtSecuritiesCurrent"],
    "debt_total": ["LongTermDebt", "DebtLongtermAndShorttermCombinedAmount", "LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities"],
    "debt_noncurrent": ["LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations", "LongTermDebtAndFinanceLeaseObligationsNoncurrent"],
    "debt_current": ["LongTermDebtCurrent", "DebtCurrent", "LongTermDebtAndCapitalLeaseObligationsCurrent"],
    "st_borrowings": ["ShortTermBorrowings", "CommercialPaper", "LinesOfCreditCurrent"],
    "nci": ["MinorityInterest"],
    "preferred": ["PreferredStockValue"],
    "assets_current": ["AssetsCurrent"],
    "liabilities_current": ["LiabilitiesCurrent"],
}

def days(a, b): return (datetime.date.fromisoformat(b) - datetime.date.fromisoformat(a)).days

def _units(facts, tag, ns="us-gaap"):
    node = facts.get("facts", {}).get(ns, {}).get(tag)
    if not node: return []
    u = node.get("units", {})
    return u.get("USD") or u.get("shares") or next(iter(u.values()), [])

def _src(tag, e): return {"tag": tag, "form": e.get("form"), "period": f"{e.get('start', '')}..{e['end']}".lstrip("."), "filed": e.get("filed"), "accn": e.get("accn")}

def duration_series(facts, tags):
    """{end: (val, start, src)} for every reported period, latest filing winning; tags merged by priority."""
    out = {}
    for tag in reversed(tags):  # lower priority first, overwritten by higher
        best = {}
        for e in _units(facts, tag):
            if "start" not in e or e.get("form", "").startswith(("8-K", "S-", "424")): continue
            k = (e["start"], e["end"])
            if k not in best or (e.get("filed") or "") > (best[k].get("filed") or ""): best[k] = e
        for (s, en), e in best.items(): out[(s, en)] = (e["val"], s, _src(tag, e))
    return out

def annual(series):
    """Fiscal-year values: periods of 350-380 days, keyed by end date."""
    return {en: v for (s, en), v in series.items() if 350 <= days(s, en) <= 380}

def ltm(series):
    """LTM = latest fiscal year + current YTD - prior-year YTD, when a 10-Q period ends after the fiscal year; else the fiscal year."""
    ann = annual(series)
    if not ann: return None, None
    fy_end = max(ann); fy_val, fy_start, fy_src = ann[fy_end]
    ytd = [(en, s, v) for (s, en), v in series.items() if en > fy_end and s > fy_end and 80 <= days(s, en) <= 290 and days(fy_end, s) <= 5]
    if not ytd: return fy_val, {"basis": "fiscal year", "period": f"{fy_start}..{fy_end}", "sources": [fy_src]}
    en, s, cur = max(ytd)
    L = days(s, en); prior = [(v, ps, pe) for (ps, pe), v in series.items() if abs(days(pe, en) - 365) <= 10 and abs(days(ps, pe) - L) <= 10]
    if not prior: return fy_val, {"basis": "fiscal year (no prior-year YTD)", "period": f"{fy_start}..{fy_end}", "sources": [fy_src]}
    pv = prior[0][0]
    return fy_val + cur[0] - pv[0], {"basis": "LTM", "period": f"FY ending {fy_end} + YTD to {en} - prior YTD", "ending": en, "sources": [fy_src, cur[2], pv[2]]}

def instant_series(facts, tags):
    out = {}
    for tag in reversed(tags):
        for e in _units(facts, tag):
            if "start" in e: continue
            if e["end"] not in out or tag in tags[:1] or (e.get("filed") or "") >= (out[e["end"]][1].get("filed") or ""):
                out[e["end"]] = (e["val"], _src(tag, e))
    return out

def latest(series, on_or_before=None):
    keys = sorted(k for k in series if not on_or_before or k <= on_or_before)
    return (keys[-1], *series[keys[-1]]) if keys else (None, None, None)

def financials(facts, years=5):
    """Annual history (last `years` fiscal years), LTM flows, and the latest balance-sheet items, in $mm."""
    flows = {k: duration_series(facts, t) for k, t in TAGS.items()}
    inst = {k: instant_series(facts, t) for k, t in INSTANT.items()}
    ann_rev = annual(flows["revenue"]); ends = sorted(ann_rev)[-years:]
    hist = []
    for en in ends:
        row = {"period_end": en, "fy": int(en[:4]) if int(en[5:7]) >= 6 else int(en[:4]) - 1}  # a year ending Jan-May is the prior fiscal year
        src = {}
        for k in TAGS:
            a = annual(flows[k]); hit = a.get(en) or next((v for e2, v in a.items() if abs(days(e2, en)) <= 7), None)
            row[k] = mm(hit[0]) if hit else None
            if hit: src[k] = hit[2]
        for k in ("assets_current", "liabilities_current", "cash", "st_investments", "debt_current", "st_borrowings"):
            hit = inst[k].get(en)
            row[k] = mm(hit[0]) if hit else None
            if hit: src[k] = hit[1]
        row["nwc"] = None
        if row["assets_current"] is not None and row["liabilities_current"] is not None:
            row["nwc"] = (row["assets_current"] - (row["cash"] or 0) - (row["st_investments"] or 0)) - (row["liabilities_current"] - (row["debt_current"] or 0) - (row["st_borrowings"] or 0))
        row["sources"] = src; hist.append(row)
    L = {}; Ls = {}
    for k in TAGS:
        v, meta = ltm(flows[k]); L[k] = mm(v) if v is not None else None
        if meta: Ls[k] = meta
    bs_date = max((latest(inst[k])[0] or "") for k in ("cash", "debt_total", "debt_noncurrent")) or None
    bs = {}; bss = {}
    for k in INSTANT:
        d, v, s = latest(inst[k], bs_date)
        fresh = d is not None and bs_date is not None and days(d, bs_date) <= 100
        bs[k] = mm(v) if fresh else None
        if fresh: bss[k] = s
    if bs.get("debt_total") is not None:
        debt = bs["debt_total"] + (bs.get("st_borrowings") or 0)
        basis = "total debt tag + short-term borrowings"
    else:
        debt = sum(bs.get(k) or 0 for k in ("debt_noncurrent", "debt_current", "st_borrowings")); basis = "noncurrent + current portion + short-term borrowings"
    balance = {"as_of": bs_date, "cash": (bs.get("cash") or 0) + (bs.get("st_investments") or 0), "debt": debt, "debt_basis": basis,
               "nci": bs.get("nci") or 0, "preferred": bs.get("preferred") or 0, "sources": bss,
               "notes": [] if bs.get("cash") is not None else ["no cash tag found; cash set to 0"]}
    return hist, {"values": L, "sources": Ls}, balance

def shares_out(facts):
    """Latest dei:EntityCommonStockSharesOutstanding (cover page, sum across classes on the same date), else diluted weighted average."""
    rows = [e for e in _units(facts, "EntityCommonStockSharesOutstanding", "dei") if "end" in e]
    if rows:
        d = max(e["end"] for e in rows); same = {}
        for e in rows:
            if e["end"] == d:
                key = (e.get("accn"), e.get("frame")); same[key] = e
        accn = max(same.values(), key=lambda e: e.get("filed") or "")["accn"]
        total = sum(e["val"] for e in same.values() if e.get("accn") == accn)
        return mm(total), {"tag": "dei:EntityCommonStockSharesOutstanding", "as_of": d, "accn": accn, "basis": "basic shares on the latest cover page"}
    s = duration_series(facts, ["WeightedAverageNumberOfDilutedSharesOutstanding"])
    if s:
        (st, en), (v, _, src) = max(s.items(), key=lambda kv: kv[0][1])
        return mm(v), {**src, "basis": "diluted weighted average (no cover-page count)"}
    return None, {"basis": "not found"}

# ---- market data ---------------------------------------------------------------------------------------------------
def yahoo_closes(symbol, years=2):
    r = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}", params={"range": f"{years}y", "interval": "1d"}, headers={"User-Agent": "Mozilla/5.0"}, gap=0.3)
    res = r.json()["chart"]["result"][0]; ts = res["timestamp"]; cl = res["indicators"]["quote"][0]["close"]
    adj = (res["indicators"].get("adjclose") or [{}])[0].get("adjclose") or cl
    return [(datetime.datetime.utcfromtimestamp(t).date().isoformat(), c, a) for t, c, a in zip(ts, cl, adj) if c is not None]

def stooq_closes(symbol, years=2):
    s = symbol.lower().replace("^gspc", "^spx"); s = s if s.startswith("^") or "." in s else s + ".us"
    r = get("https://stooq.com/q/d/l/", params={"s": s, "i": "d"}, gap=0.3)
    rows = list(csv.DictReader(io.StringIO(r.text))); cut = (datetime.date.today() - datetime.timedelta(days=365 * years)).isoformat()
    return [(x["Date"], float(x["Close"]), float(x["Close"])) for x in rows if x.get("Close") and x["Date"] >= cut]

def closes(symbol, years=2):
    errs = []
    for f in (yahoo_closes, stooq_closes):
        try:
            out = f(symbol, years)
            if len(out) > 100: return out, f.__name__.split("_")[0]
        except Exception as e: errs.append(f"{f.__name__}: {e}")
    raise RuntimeError(f"no price history for {symbol}: {'; '.join(errs)}")

def weekly_beta(px, mkt):
    """OLS beta of weekly (Friday-to-Friday, last close of each ISO week) total returns, from adjusted closes."""
    def wk(series):
        out = {}
        for d, _, a in series: out[datetime.date.fromisoformat(d).isocalendar()[:2]] = a
        return out
    a, b = wk(px), wk(mkt); keys = sorted(set(a) & set(b))
    ra = [a[k] / a[j] - 1 for j, k in zip(keys, keys[1:])]; rb = [b[k] / b[j] - 1 for j, k in zip(keys, keys[1:])]
    if len(ra) < 52: return None, len(ra)
    mb, ma = statistics.fmean(rb), statistics.fmean(ra)
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb)); var = sum((y - mb) ** 2 for y in rb)
    return (cov / var if var else None), len(ra)

def price_block(sym, mkt, as_of):
    px, src = closes(sym)
    px = [p for p in px if p[0] <= as_of]
    last_d, last, _ = px[-1]; yr = [p for p in px if p[0] > (datetime.date.fromisoformat(last_d) - datetime.timedelta(days=365)).isoformat()]
    beta, n = weekly_beta(px, mkt) if mkt else (None, 0)
    vw = [p[1] for p in px[-30:]]
    return {"last": round(last, 4), "date": last_d, "high_52w": round(max(p[1] for p in yr), 4), "low_52w": round(min(p[1] for p in yr), 4),
            "avg_30d": round(sum(vw) / len(vw), 4), "history_1y": [[d, round(c, 4)] for d, c, _ in yr], "source": src,
            "beta_raw": None if beta is None else round(beta, 3), "beta_basis": f"2-year weekly vs S&P 500 ({n} weeks)" if beta is not None else "not enough history"}

def risk_free(as_of):
    try:
        r = get("https://fred.stlouisfed.org/graph/fredgraph.csv", params={"id": "DGS10", "cosd": (datetime.date.fromisoformat(as_of) - datetime.timedelta(days=20)).isoformat(), "coed": as_of}, headers={"User-Agent": "Mozilla/5.0"}, gap=0.3)
        rows = [x for x in csv.reader(io.StringIO(r.text))][1:]; rows = [(d, float(v)) for d, v in rows if v not in (".", "")]
        d, v = rows[-1]; return {"rate": round(v / 100, 5), "date": d, "source": "FRED DGS10 (10-year U.S. Treasury, constant maturity)"}
    except Exception as e:
        return {"rate": None, "date": None, "source": f"FRED unavailable ({e}); set the risk-free rate on the Assumptions tab"}

# ---- companies -----------------------------------------------------------------------------------------------------
def ticker_map():
    j = sec_json("https://www.sec.gov/files/company_tickers.json")
    return {v["ticker"].upper(): (int(v["cik_str"]), v["title"]) for v in j.values()}

def company(ticker, cik, mkt, as_of, light=False):
    sub = sec_json(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
    facts = sec_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json")
    hist, L, bal = financials(facts, years=2 if light else 5)
    sh, shs = shares_out(facts)
    rec = {"ticker": ticker, "cik": cik, "name": sub.get("name"), "sic": sub.get("sic"), "sic_description": sub.get("sicDescription"),
           "exchange": (sub.get("exchanges") or [None])[0], "fiscal_year_end": sub.get("fiscalYearEnd"), "state_of_incorporation": sub.get("stateOfIncorporation"),
           "annual": hist, "ltm": L, "balance": bal, "shares_out_mm": sh, "shares_source": shs}
    try: rec["price"] = price_block(ticker.replace(".", "-"), mkt, as_of)
    except Exception as e: rec["price"] = None; rec.setdefault("notes", []).append(str(e))
    if light: rec.pop("annual")
    return rec

def sic_candidates(sic, tmap, exclude_cik):
    r = get("https://www.sec.gov/cgi-bin/browse-edgar", params={"action": "getcompany", "SIC": sic, "type": "10-K", "owner": "include", "count": 100}, headers={"User-Agent": sec_ua()})
    ciks = {int(c) for c in re.findall(r"CIK=(\d{10})", r.text)}
    by_cik = {}
    for t, (c, name) in tmap.items():
        if c in ciks and c != exclude_cik and "-" not in t and len(t) <= 5: by_cik.setdefault(c, t)  # first listed ticker; skips preferred/warrant lines
    return [(t, c) for c, t in by_cik.items()]

def pick_peers(target, cands, mkt, as_of, max_peers, log):
    rev0 = target["ltm"]["values"].get("revenue") or 0; scored = []
    for t, c in cands[:30]:
        try: p = company(t, c, mkt, as_of, light=True)
        except Exception as e: log(f"  skip {t}: {e}"); continue
        rev = p["ltm"]["values"].get("revenue"); eb = p["ltm"]["values"].get("ebit")
        if not rev or not p.get("price") or not p.get("shares_out_mm") or rev0 <= 0: log(f"  skip {t}: missing revenue, price or shares"); continue
        ratio = rev / rev0
        if not 0.2 <= ratio <= 5: log(f"  skip {t}: revenue {ratio:.2f}x the target's"); continue
        scored.append((abs(math.log(ratio)), t, p)); log(f"  candidate {t} {p['name'][:40]} revenue {ratio:.2f}x")
    scored.sort(key=lambda x: x[0]); return [p for _, _, p in scored[:max_peers]]

def run(ticker, out, peers=None, max_peers=6, as_of=None, log=print):
    as_of = as_of or datetime.date.today().isoformat(); ticker = ticker.upper()
    tmap = ticker_map()
    if ticker not in tmap: raise SystemExit(f"{ticker} is not in the SEC ticker list (company_tickers.json)")
    cik, _ = tmap[ticker]
    mkt, msrc = closes("^GSPC"); log(f"S&P 500 history: {len(mkt)} days ({msrc})")
    tgt = company(ticker, cik, mkt, as_of); log(f"{ticker} CIK {cik} {tgt['name']} SIC {tgt['sic']} {tgt['sic_description']}")
    if peers:
        chosen = []
        for t in peers:
            t = t.strip().upper()
            if t not in tmap: log(f"  peer {t} not in the SEC ticker list; skipped"); continue
            chosen.append(company(t, tmap[t][0], mkt, as_of, light=True))
        basis = "named by the user (--peers)"
    else:
        cands = sic_candidates(tgt["sic"], tmap, cik); log(f"SIC {tgt['sic']}: {len(cands)} listed candidates")
        chosen = pick_peers(tgt, cands, mkt, as_of, max_peers, log); basis = f"same SIC code ({tgt['sic']} {tgt['sic_description']}), revenue within 0.2x-5x of the target's, closest {max_peers} by revenue"
    doc = {"schema": SCHEMAS["company"], "as_of": as_of, "units": "$ in millions, shares in millions, per-share in $", "target": tgt,
           "peers": chosen, "peer_basis": basis, "market": {"risk_free": risk_free(as_of), "index": "S&P 500 (^GSPC)"}}
    p = save(doc, Path(out) / "company.json"); log(f"wrote {p} ({len(chosen)} peers)"); return doc

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("ticker"); ap.add_argument("out"); ap.add_argument("--peers", default=None); ap.add_argument("--max-peers", type=int, default=6); ap.add_argument("--as-of", default=None)
    a = ap.parse_args(); run(a.ticker, a.out, a.peers.split(",") if a.peers else None, a.max_peers, a.as_of)
