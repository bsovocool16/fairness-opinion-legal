"""One row per (deal, bank): pick the best filing per target CIK + 18-month window, first DCF block per bank."""
import pandas as pd, numpy as np
d = pd.read_csv("data/blocks_all.csv", low_memory=False)
d["date"] = pd.to_datetime(d["date"])
d = d[~d.is_book & d.bank.notna() & d.dr_lo.notna()].copy()
pri = {"DEFM14A": 0, "DEFM14C": 1, "SC 14D9": 2, "SC 13E3": 3, "SC TO-T": 4, "SC 14D9/A": 5, "SC 13E3/A": 6, "SC TO-T/A": 7}
d["fpri"] = d.form.map(pri).fillna(9)
d = d.sort_values(["cik", "date"])
# deal id: same target CIK within 540 days of the deal's first filing
deal, last = [], {}
did = 0
for cik, dt in zip(d.cik, d.date):
    if cik in last and (dt - last[cik][1]).days <= 540: deal.append(last[cik][0])
    else: did += 1; last[cik] = (did, dt); deal.append(did)
d["deal_id"] = deal
d = d.sort_values(["deal_id", "fpri", "date", "acc", "block_i"])
best_doc = d.groupby("deal_id").head(1)[["deal_id", "acc", "doc"]].rename(columns={"acc": "bacc", "doc": "bdoc"})
d = d.merge(best_doc, on="deal_id")
# banks found in the preferred doc come from it; banks only present in other filings (e.g. 13E3 exhibit summaries) are added once
d["in_best"] = (d.acc == d.bacc) & (d.doc == d.bdoc)
d = d.sort_values(["deal_id", "bank", "in_best", "fpri", "block_i"], ascending=[True, True, False, True, True])
db = d.groupby(["deal_id", "bank"]).head(1).copy()
db["year"] = db.date.dt.year
db.to_csv("data/deal_bank.csv", index=False)
print("deal-bank rows", len(db), "deals", db.deal_id.nunique(), "years", db.year.min(), db.year.max())
print(db.groupby("year").size().to_string())
