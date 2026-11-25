import sys, os, re, time, requests
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "fairness-opinion-legal", "scripts"))
os.environ.setdefault("EDGAR_UA", "fo-research-project contact@example.org")
from edgar_precedents import html_to_text
UA = {"User-Agent": os.environ["EDGAR_UA"]}
def fetch(cik, acc, doc):
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-','')}/{doc}"
    for a in range(5):
        try:
            r = requests.get(url, headers=UA, timeout=90)
            if r.status_code == 200: return r.content.decode("utf-8", "replace")
            if r.status_code == 404: return None
            time.sleep(2 * (a + 1))
        except Exception: time.sleep(2 * (a + 1))
    return None
