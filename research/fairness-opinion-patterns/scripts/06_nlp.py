"""House-style fingerprinting: can the bank be identified from its DCF paragraph alone (bank names masked)?"""
import pandas as pd, numpy as np, re, json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from banks import BANK_RX
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import accuracy_score, confusion_matrix
d = pd.read_csv("data/analysis_deal_bank.csv", low_memory=False)
tx = pd.read_json("data/blocks_text.jsonl.gz", lines=True)
m = d.merge(tx, on=["acc", "doc", "block_i", "bank"])
top = m.bank_name.value_counts().head(15).index
m = m[m.bank_name.isin(top)].copy()
def mask(t):
    t = re.sub(r"\s+", " ", t)
    for _, _, rx in BANK_RX: t = rx.sub(" BANK ", t)
    t = re.sub(r"\$\s?\d[\d,.]*", " $NUM ", t); t = re.sub(r"\d+(?:\.\d+)?\s*%", " PCT ", t); t = re.sub(r"\d+(?:\.\d+)?x\b", " MULT ", t)
    t = re.sub(r"\b(?:19|20)\d\d\b", " YEAR ", t); t = re.sub(r"\d+", " N ", t)
    t = re.sub(r"\b[A-Z][a-zA-Z&'.-]+\b", lambda x: x.group(0) if x.group(0) in ("BANK", "PCT", "MULT", "YEAR", "NUM", "CAPM", "EBITDA", "WACC") else " CAP ", t)   # mask proper nouns
    return t.lower()
m["mt"] = m.text.map(mask)
vec = TfidfVectorizer(ngram_range=(1, 3), min_df=3, max_features=200000, sublinear_tf=True)
X = vec.fit_transform(m.mt); y = m.bank_name.values
clf = LogisticRegression(max_iter=3000, C=10)
pred = cross_val_predict(clf, X, y, cv=StratifiedKFold(5, shuffle=True, random_state=0))
acc = accuracy_score(y, pred); base = pd.Series(y).value_counts(normalize=True).iloc[0]
print("5-fold accuracy", round(acc, 3), "majority baseline", round(base, 3), "n", len(y))
# temporal holdout: train <=2016, test >=2019
tr = m.year <= 2016; te = m.year >= 2019
clf.fit(X[tr.values], y[tr.values]); acc_t = accuracy_score(y[te.values], clf.predict(X[te.values]))
print("train<=2016 test>=2019 accuracy", round(acc_t, 3), te.sum())
# per-bank recall
rec = pd.crosstab(pd.Series(y, name="true"), pd.Series(pred, name="pred"))
per = (np.diag(rec.values) / rec.sum(1).values)
perbank = dict(zip(rec.index, np.round(per, 3)))
print(perbank)
# signature n-grams
clf.fit(X, y); fn = np.array(vec.get_feature_names_out())
sig = {}
for i, b in enumerate(clf.classes_):
    co = clf.coef_[i]; idx = np.argsort(co)[::-1]
    sig[b] = [f for f in fn[idx] if len(f.split()) >= 2 and "cap" not in f.split() and "bank" != f][:12]
    print(b, "|", "; ".join(sig[b][:8]))
# within-bank textual drift: mean cosine similarity of each bank's paragraphs to its own centroid by year
from sklearn.preprocessing import normalize
Xn = normalize(X)
drift = {}
for b in top:
    sel = (m.bank_name == b).values
    for yr in sorted(m.year[sel].unique()):
        s2 = sel & (m.year == yr).values
        if s2.sum() < 5: continue
        c = np.asarray(Xn[s2].mean(0)); sim = np.asarray(Xn[s2] @ c.T).ravel() / np.linalg.norm(c)
        drift.setdefault(b, {})[int(yr)] = float(sim.mean())
# cross-bank similarity: same-bank pairs vs different-bank pairs (random sample)
rng = np.random.default_rng(0); n = len(y); i1 = rng.integers(0, n, 20000); i2 = rng.integers(0, n, 20000)
sims = np.asarray(Xn[i1].multiply(Xn[i2]).sum(1)).ravel(); same = y[i1] == y[i2]
print("cosine same-bank", sims[same & (i1 != i2)].mean().round(3), "diff-bank", sims[~same].mean().round(3))
labels = list(rec.index)
json.dump({"acc_cv": acc, "baseline": base, "n": int(len(y)), "acc_temporal": acc_t, "n_temporal": int(te.sum()), "per_bank_recall": {k: float(v) for k, v in perbank.items()},
           "signatures": sig, "drift": drift, "cos_same": float(sims[same & (i1 != i2)].mean()), "cos_diff": float(sims[~same].mean()),
           "confusion": {"labels": labels, "matrix": rec.values.tolist()}}, open("data/nlp_results.json", "w"), indent=1)
