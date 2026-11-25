"""Collect every number and chart series the post uses into data/results.json."""
import pandas as pd, numpy as np, json, statsmodels.formula.api as smf
R = {}
d = pd.read_csv("data/analysis_deal_bank.csv", low_memory=False)
d = d[d.dr_mid <= 25].copy()
for c in [c for c in d.columns if c.startswith("f_")] + ["cash_deal", "stock_deal", "is_13e3", "special_committee", "sponsor"]:
    d[c] = d[c].astype(str) == "True"
R["n_rows"] = int(len(d)); R["n_deals"] = int(d.deal_id.nunique()); R["n_banks"] = int(d.bank.nunique())
R["year_min"], R["year_max"] = int(d.year.min()), int(d.year.max())
R["n_filings"] = 8344
R["by_year"] = d.groupby("year").size().to_dict()
cash = d[d.deal_type.isin(["strategic cash", "sponsor cash", "13e-3 / going private"])]
p = cash.pos.dropna()
R["pos"] = {"n": int(len(p)), "below": float((p < 0).mean()), "inside": float(((p >= 0) & (p <= 1)).mean()), "above": float((p > 1).mean()), "median": float(p.median())}
edges = np.round(np.arange(-1.0, 2.0001, 0.05), 2)
h, _ = np.histogram(p.clip(-1.0, 1.9999), edges)
R["pos_hist"] = [{"x0": float(a), "x1": float(b), "n": int(n)} for a, b, n in zip(edges[:-1], edges[1:], h)]
R["pos_by_type"] = []
for t, g in cash.groupby("deal_type"):
    q = g.pos.dropna(); R["pos_by_type"].append({"type": t, "n": int(len(q)), "below": float((q < 0).mean()), "inside": float(((q >= 0) & (q <= 1)).mean()), "above": float((q > 1).mean()), "median": float(q.median())})
r = (1 / cash.price_to_mid).dropna()
R["bank_ratio"] = {"q": r.quantile([.1, .25, .5, .75, .9]).round(3).tolist(), "n": int(len(r))}
rng = np.random.default_rng(1)
R["bank_ratio_sample"] = np.round(rng.choice(r.values, 300, replace=False), 3).tolist()
a = pd.read_csv("data/appraisal/appraisal_cases.csv")
dp = pd.to_numeric(a.deal_price_per_share, errors="coerce")
R["appraisal"] = {}
for c, k in [("petitioner_expert_value", "petitioner"), ("respondent_expert_value", "respondent"), ("court_fair_value_per_share", "court")]:
    x = (pd.to_numeric(a[c], errors="coerce") / dp)
    keep = x.notna() & ~a.case_name.duplicated()
    R["appraisal"][k] = {"values": [{"case": n, "v": round(float(v), 3), "year": str(y)[:4]} for n, v, y in zip(a.case_name[keep], x[keep], a.date[keep])], "q": x[keep].quantile([.1, .25, .5, .75, .9]).round(3).tolist(), "n": int(keep.sum())}
a["yr"] = pd.to_numeric(a.date.astype(str).str[:4], errors="coerce")
a["pct"] = pd.to_numeric(a.fv_pct_of_deal, errors="coerce")
R["appraisal_era"] = {e: {"n": int(g.pct.notna().sum()), "median": float(g.pct.median())} for e, g in a.drop_duplicates("case_family", keep="last").groupby(a.yr >= 2018)}
erp = pd.to_numeric(a.court_erp, errors="coerce"); R["court_erp_2010"] = erp[a.yr >= 2010].dropna().round(2).tolist()
R["court_growth"] = pd.to_numeric(a.court_perpetuity_growth, errors="coerce").dropna().tolist()
R["court_wacc"] = pd.to_numeric(a.court_wacc, errors="coerce")[a.yr >= 2010].dropna().tolist()
# heaping
x = pd.concat([d.dr_lo, d.dr_hi]).dropna(); frac = (x * 100).round().astype(int) % 100
R["heap"] = {"integer": float((frac == 0).mean()), "half": float((frac == 50).mean()), "quarter": float(frac.isin([25, 75]).mean()), "other": float((~frac.isin([0, 25, 50, 75])).mean()), "n": int(len(x))}
R["dr_width"] = (d.dr_w.round(2).value_counts(normalize=True).head(8)).round(4).to_dict()
pg = d[d.pg_lo.notna()]
R["pg_pairs"] = (pg.apply(lambda r: f"{r.pg_lo:g}–{r.pg_hi:g}%", axis=1).value_counts(normalize=True).head(10)).round(4).to_dict()
R["pg_width"] = (pg.pg_w.round(2).value_counts(normalize=True).head(5)).round(4).to_dict()
em = d[d.em_lo.notna()]; emx = pd.concat([em.em_lo, em.em_hi]); f2 = ((emx * 10).round() % 10)
R["em_heap"] = {"whole": float((f2 == 0).mean()), "half": float((f2 == 5).mean())}
R["n_pg"], R["n_em"] = int(len(pg)), int(len(em))
R["pg_median"] = float(pg.pg_mid.median())
# rates
mk = pd.read_csv("data/market_monthly.csv"); mk["year"] = mk.month.str[:4].astype(int)
yr = d.groupby("year").agg(dr=("dr_mid", "median"), n=("dr_mid", "size"), pg=("pg_mid", "median")).reset_index().merge(mk.groupby("year").tnx10y.mean().reset_index(), on="year")
R["rates"] = yr.round(3).to_dict("records")
top = d.bank.value_counts(); d["bankf"] = np.where(d.bank.map(top) >= 15, d.bank_name, "other"); d["sic2"] = d.sic2.fillna("na").astype(str)
d["period"] = pd.cut(d.year, [2000, 2012, 2021, 2026], labels=["2001–12", "2013–21", "2022–26"])
dd = d[d.tnx10y.notna()]
m = smf.ols("dr_mid ~ tnx10y:C(period) + C(period) + C(bankf) + C(sic2) + C(deal_type)", dd).fit()
R["passthrough"] = {k.split("[")[1].rstrip("]"): [round(float(m.params[k]), 3), round(float(m.bse[k]), 3)] for k in m.params.index if k.startswith("tnx10y")}
m0 = smf.ols("dr_mid ~ tnx10y + C(bankf) + C(sic2) + C(deal_type)", dd).fit(); R["passthrough_all"] = [round(float(m0.params["tnx10y"]), 3), round(float(m0.bse["tnx10y"]), 3)]
# variance decomposition
steps = []
for lab, f in [("Year", "dr_mid ~ C(year)"), ("+ Industry (SIC-2)", "dr_mid ~ C(year)+C(sic2)"), ("+ Deal type", "dr_mid ~ C(year)+C(sic2)+C(deal_type)"), ("+ Which bank", "dr_mid ~ C(year)+C(sic2)+C(deal_type)+C(bankf)")]:
    steps.append({"label": lab, "r2": round(float(smf.ols(f, d).fit().rsquared_adj), 4)})
R["r2_steps"] = steps
P = pd.read_csv("data/same_deal_pairs.csv"); P["ddr"] = (P.dr1 - P.dr2).abs()
R["pairs"] = {"n": int(len(P)), "median_bp": float(P.ddr.median() * 100), "identical": float((P.ddr < 1e-9).mean()), "p90_bp": float(P.ddr.quantile(.9) * 100),
              "hist": P.ddr.clip(upper=4).round(2).value_counts().sort_index().to_dict()}
d["grp"] = d.year.astype(str) + d.sic2
R["cross_mad_bp"] = float(d.groupby("grp").dr_mid.transform(lambda z: (z - z.median()).abs()).median() * 100)
# trends
tr = d.groupby("year").agg(perp=("tv_method", lambda s: s.isin(["perpetuity", "both"]).mean()), exitm=("tv_method", lambda s: s.isin(["exit multiple", "both"]).mean()),
                           judgment=("f_professional_judgment", "mean"), capm=("f_capm", "mean"), midyear=("f_mid_year", "mean"), rounded=("f_rounded", "mean"), sbc=("f_sbc_cash", "mean"), illustrative=("f_illustrative", "mean")).reset_index()
R["trends"] = tr.round(4).to_dict("records")
# house styles
nlp = json.load(open("data/nlp_results.json"))
top15 = d.bank_name.value_counts().head(15).index
hs = []
for b in top15:
    g = d[d.bank_name == b]; q = g[g.deal_type.isin(["strategic cash", "sponsor cash", "13e-3 / going private"])].pos.dropna()
    hs.append({"bank": b, "n": int(len(g)), "dr_w": float(g.dr_w.median()), "dr_mid": float(g.dr_mid.median()), "perp": float(g.tv_method.isin(["perpetuity", "both"]).mean()),
               "exitm": float(g.tv_method.isin(["exit multiple", "both"]).mean()), "decline": float((g.tv_method == "decline (patent cliff)").mean()), "pos": float(q.median()) if len(q) else None,
               "judgment": float(g[g.year >= 2020].f_professional_judgment.mean()), "illustrative": float(g.f_illustrative.mean()),
               "recall": nlp["per_bank_recall"].get(b), "sig": nlp["signatures"].get(b, [])[:5]})
R["house"] = hs
R["nlp"] = {k: nlp[k] for k in ["acc_cv", "baseline", "n", "acc_temporal", "n_temporal", "cos_same", "cos_diff"]}
# books
bk = pd.read_csv("data/books_features.csv")
for c in [c for c in bk.columns if c.startswith("f_")]: bk[c] = bk[c].astype(str) == "True"
bk["era"] = pd.cut(bk.year, [2000, 2008, 2015, 2021, 2026], labels=["2001–08", "2009–15", "2016–21", "2022–26"])
R["books_n"] = int(len(bk))
R["books_era"] = bk.groupby("era", observed=True).agg(n=("bank", "size"), erp=("erp", "median"), bloomberg=("f_bloomberg", "mean"), barra=("f_barra", "mean"), kroll=("f_duffphelps", "mean"), supply=("f_supply_side", "mean")).reset_index().astype({"era": str}).round(3).to_dict("records")
tb = bk.bank_name.value_counts().head(12).index
R["books_bank"] = bk[bk.bank_name.isin(tb)].groupby("bank_name").agg(n=("bank", "size"), bloomberg=("f_bloomberg", "mean"), barra=("f_barra", "mean"), kroll=("f_duffphelps", "mean"), t10=("rf_tenor", lambda s: (s == 10).sum()), t20=("rf_tenor", lambda s: (s == 20).sum()), t30=("rf_tenor", lambda s: (s == 30).sum())).reset_index().round(3).to_dict("records")
R["books_tenor"] = bk.rf_tenor.value_counts().head(3).to_dict()
# court vs banker WACC on the same deals (hand-matched; target-side DCFs only)
R["court_vs_bank"] = [
 {"case": "Dell (2016)", "court": 9.46, "banks": [["Evercore", 10.0, 12.0], ["J.P. Morgan", 9.5, 13.5]]},
 {"case": "Jarden (2019)", "court": 6.94, "banks": [["Centerview", 6.75, 7.75], ["Goldman Sachs", 6.5, 8.5]]},
 {"case": "Norcraft (2018)", "court": 10.60, "banks": [["Citi", 9.6, 11.3]]},
 {"case": "Lender Processing (2016)", "court": 9.56, "banks": [["Credit Suisse", 8.0, 10.0], ["Goldman Sachs", 8.5, 10.0]]},
 {"case": "Ancestry.com (2015)", "court": 10.71, "banks": [["Qatalyst", 9.0, 14.0]]},
 {"case": "DFC Global (2016)", "court": 10.72, "banks": [["Houlihan Lokey", 10.0, 11.0]]},
 {"case": "Clearwire (2017)", "court": 10.92, "banks": [["Centerview", 10.0, 17.5], ["Evercore", 12.5, 17.5]]},
 {"case": "AutoInfo (2015)", "court": 17.57, "banks": [["Stephens", 18.0, 20.0]]},
 {"case": "Pivotal (2024)", "court": 7.69, "banks": [["Morgan Stanley", 9.0, 11.0]]},
]
cv = R["court_vs_bank"]; R["court_below_bank_mid"] = sum(1 for c in cv if c["court"] < np.mean([(b[1] + b[2]) / 2 for b in c["banks"]]))
R["utz"] = [{"step": "First model: raw 2-yr betas, 10-yr rf, 5.5% ERP", "wacc": 5.0}, {"step": "5-year weekly Blume-adjusted betas + debt beta", "wacc": 6.2},
            {"step": "+ Utz's own asset beta", "wacc": 6.5}, {"step": "+ 20/30-yr risk-free rate", "wacc": 6.7}, {"step": "All three + 6.5% ERP", "wacc": 7.4}, {"step": "Citi's range (midpoint 8.2%)", "wacc": 8.2}]
json.dump(R, open("data/results.json", "w"), indent=1, default=float)
print(json.dumps({k: R[k] for k in ["pos", "pos_by_type", "bank_ratio", "heap", "passthrough", "passthrough_all", "r2_steps", "pairs", "cross_mad_bp", "nlp", "court_below_bank_mid", "appraisal_era", "books_tenor"]}, indent=0, default=float))
# extras for the page
R["book_erp_2010"] = bk[(bk.year >= 2010) & bk.erp.notna()].erp.round(2).tolist()
R["book_erp_pre2010"] = bk[(bk.year < 2010) & bk.erp.notna()].erp.round(2).tolist()
bins = np.arange(0, 4.26, 0.25); hh, _ = np.histogram(P.ddr.clip(upper=4.0), np.append(bins, 9))
R["pairs_hist"] = [{"x": float(b), "n": int(n)} for b, n in zip(bins, hh)]
R["bank_pg_values"] = pg.pg_mid.round(2).tolist()
json.dump(R, open("data/results.json", "w"), indent=0, default=float)
