"""Board-book (SC 13E3 / SC TO exhibit) WACC build-up fields, attributed to the bank that prepared the book."""
import json, gzip, sys, os, re, pandas as pd, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from banks import first_bank, DISPLAY, BANK_RX
from collections import Counter
books = json.load(open("data/books.json"))
rows = []
for b in books:
    p = f"data/raw/{b['acc']}__{b['doc'].replace('/','_')}.txt.gz"
    t = gzip.open(p, "rt").read()
    # a board book names its author on nearly every page (footers, disclaimers): take the most frequent bank
    c = Counter()
    for k, _, rx in BANK_RX: c[k] = len(rx.findall(t))
    k, n = c.most_common(1)[0]
    if n < 3: continue
    is_deck = bool(re.search(r"(?i)discussion materials|presentation to|board of directors|special committee", t[:6000]))
    def pick(vals, lo, hi):
        v = [x for x in vals if lo <= x <= hi]
        return float(np.median(v)) if v else None
    rows.append({**{k2: b[k2] for k2 in ["acc", "doc", "form", "date", "target", "cik"]}, "bank": k, "bank_name": DISPLAY.get(k, k), "is_deck": is_deck,
                 "rf": pick(b["rf"], 0.2, 8), "erp": pick(b["erp"], 3, 9.5), "size": pick(b["size"], 0.1, 7), "ubeta": pick(b["ubeta"], 0.1, 2.5),
                 "rf_tenor": b.get("rf_tenor"), **{k2: b[k2] for k2 in b if k2.startswith("f_")}})
df = pd.DataFrame(rows); df["year"] = pd.to_datetime(df.date).dt.year
# one per deal (CIK + year) per bank
df = df.sort_values("date").drop_duplicates(["cik", "bank", "year"])
df.to_csv("data/books_features.csv", index=False)
print(len(df), df.bank_name.value_counts().head(12).to_dict())
for c in ["rf", "erp", "size", "ubeta", "rf_tenor"]: print(c, df[c].notna().sum())
