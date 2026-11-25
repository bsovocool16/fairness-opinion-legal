"""Run the extractors over every downloaded document and write the analysis tables."""
import json, gzip, glob, os, sys, csv, re
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from extract import extract_doc
from extract_book import extract_book
import pandas as pd
idx = json.load(open("data/index.json"))
bykey = {f"{v['acc']}__{v['doc'].replace('/','_')}": v for v in idx.values()}
def one(p):
    key = os.path.basename(p)[:-7]; v = bykey.get(key)
    if not v: return [], None
    try: t = gzip.open(p, "rt").read()
    except Exception: return [], None
    form = (v["form"] or "")
    is_book = form.startswith(("SC 13E3", "SC TO")) and (v.get("file_type") or "").upper().startswith("EX")
    meta = {"acc": v["acc"], "doc": v["doc"], "form": form, "date": v["date"], "target": (v["names"] or [""])[0], "cik": (v["ciks"] or [""])[0],
            "sic": (v["sics"] or [""])[0] if v.get("sics") else "", "file_type": v.get("file_type"), "is_book": is_book}
    rows, flags = extract_doc(t)
    out = []
    for r in rows:
        r = {**meta, **flags, **r}; out.append(r)
    book = None
    if is_book:
        book = {**meta, **extract_book(t)}
    return out, book
if __name__ == "__main__":
    files = glob.glob("data/raw/*.txt.gz"); print("docs", len(files))
    blocks, books = [], []
    with ProcessPoolExecutor(4) as ex:
        for out, book in ex.map(one, files, chunksize=20):
            blocks += out
            if book: books.append(book)
    df = pd.DataFrame(blocks)
    df.drop(columns=["text"]).to_csv("data/blocks_all.csv", index=False)
    df[["acc", "doc", "block_i", "bank", "text"]].to_json("data/blocks_text.jsonl.gz", orient="records", lines=True, compression="gzip")
    json.dump(books, open("data/books.json", "w"))
    print("blocks", len(df), "books", len(books))
