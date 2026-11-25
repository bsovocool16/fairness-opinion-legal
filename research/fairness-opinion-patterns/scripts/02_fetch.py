"""Download each indexed document, convert to text, store gzipped. Resumable."""
import json, gzip, os, sys, time, threading
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from common import fetch, html_to_text
idx = json.load(open("data/index.json"))
want = sys.argv[1].split(",") if len(sys.argv) > 1 else None
items = [v for v in idx.values() if (not want or (v["form"] or "").split("/")[0] in want)]
# main docs for proxies/14D9; exhibits only for 13E3/TO (board books)
def keep(v):
    ft = (v.get("file_type") or "").upper(); f = (v["form"] or "")
    if f.startswith(("SC 13E3", "SC TO")): return ft.startswith("EX-99") or ft.startswith("EX-(C)") or "(C)" in ft
    return not ft.startswith("EX-") or ft.startswith("EX-99")
items = [v for v in items if keep(v)]
print("to fetch", len(items), flush=True)
lock = threading.Lock(); done = [0]; last = [0.0]
def throttle():
    with lock:
        now = time.time(); wait = last[0] + 0.12 - now
        if wait > 0: time.sleep(wait)
        last[0] = time.time()
def work(v):
    p = f"data/raw/{v['acc']}__{v['doc'].replace('/','_')}.txt.gz"
    if os.path.exists(p) or os.path.exists(p.replace(".txt.gz", ".html.gz").replace("data/raw/", "data/html/")): return
    if not v["doc"].lower().endswith((".htm", ".html", ".txt")): return
    throttle()
    h = None
    for cik in v["ciks"] or []:
        h = fetch(cik, v["acc"], v["doc"])
        if h: break
    if not h: return
    with gzip.open(p.replace(".txt.gz", ".html.gz").replace("data/raw/", "data/html/"), "wt") as f: f.write(h)
    with lock:
        done[0] += 1
        if done[0] % 100 == 0: print("done", done[0], flush=True)
with ThreadPoolExecutor(14) as ex: list(ex.map(work, items))
print("finished", done[0])
