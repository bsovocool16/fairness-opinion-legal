"""Convert downloaded HTML to text (process pool)."""
import glob, gzip, os, sys
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from common import html_to_text
def conv(p):
    q = p.replace("data/html/", "data/raw/").replace(".html.gz", ".txt.gz")
    if os.path.exists(q): return 0
    h = gzip.open(p, "rt").read()
    try: t = html_to_text(h) if "<" in h[:20000] else h
    except Exception: t = h
    with gzip.open(q, "wt") as f: f.write(t)
    return 1
if __name__ == "__main__":
    fs = glob.glob("data/html/*.html.gz")
    with ProcessPoolExecutor(3) as ex: print(sum(ex.map(conv, fs, chunksize=8)))
