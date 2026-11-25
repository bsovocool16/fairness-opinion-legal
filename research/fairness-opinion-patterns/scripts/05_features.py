import pandas as pd, numpy as np, re, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from banks import TIER, DISPLAY
db = pd.read_csv("data/deal_bank.csv", low_memory=False, parse_dates=["date"])
mk = pd.read_csv("data/market_monthly.csv"); mk["month"] = pd.PeriodIndex(mk.month, freq="M")
db["month"] = db.date.dt.to_period("M")
db = db.merge(mk, on="month", how="left")
db["bank_name"] = db.bank.map(lambda b: DISPLAY.get(b, b.replace("other:", "") if isinstance(b, str) else b))
db["tier"] = db.bank.map(lambda b: TIER.get(b, "other"))
# sanity filters on discount rates (equity-level and early-stage biotech rates can be high; drop impossible)
db = db[(db.dr_lo >= 3) & (db.dr_hi <= 40) & (db.dr_hi >= db.dr_lo)].copy()
db["dr_mid"] = (db.dr_lo + db.dr_hi) / 2; db["dr_w"] = db.dr_hi - db.dr_lo
db["pg_mid"] = (db.pg_lo + db.pg_hi) / 2; db["pg_w"] = db.pg_hi - db.pg_lo
db["em_mid"] = (db.em_lo + db.em_hi) / 2
db["tv_method"] = np.select([db.pg_lo.notna() & db.em_lo.notna(), db.pg_lo.notna(), db.em_lo.notna()], ["both", "perpetuity", "exit multiple"], "unstated")
db.loc[(db.tv_method == "unstated") & db.f_tv_decline.astype(bool), "tv_method"] = "decline (patent cliff)"
# deal price: explicit comparison in the DCF paragraph first, else headline cash price
price = db.cmp_price.where(db.cmp_price.notna(), db.headline_price.where(db.cash_deal & ~db.stock_deal))
db["price"] = price
ok = db.v_lo.notna() & db.price.notna() & (db.v_hi > db.v_lo)
mid = (db.v_lo + db.v_hi) / 2
ok &= (db.price / mid).between(0.33, 3.0)
db["pos"] = np.where(ok, (db.price - db.v_lo) / (db.v_hi - db.v_lo), np.nan)
db["price_to_mid"] = np.where(ok, db.price / mid, np.nan)
db["v_width_pct"] = np.where(db.v_lo.notna(), (db.v_hi - db.v_lo) / mid, np.nan)
db["era"] = pd.cut(db.year, [2000, 2007, 2015, 2021, 2026], labels=["2001-07", "2008-15 (ZIRP/QE)", "2016-21", "2022-26 (higher rates)"])
db["deal_type"] = np.select([db.is_13e3, db.sponsor & db.cash_deal, db.stock_deal & ~db.cash_deal, db.cash_deal], ["13e-3 / going private", "sponsor cash", "stock", "strategic cash"], "other")
db["sic2"] = db.sic.astype(str).str.extract(r"(\d{2})")[0]
db.to_csv("data/analysis_deal_bank.csv", index=False)
print(len(db), "rows; with price position", db.pos.notna().sum())
