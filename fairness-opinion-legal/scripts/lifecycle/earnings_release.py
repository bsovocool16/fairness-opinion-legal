"""Management's non-GAAP figures from the target's latest earnings release (the 8-K Item 2.02 exhibit), filed on or before
the as-of date. XBRL carries no non-GAAP measures, so this is the only public source of the Adjusted EBITDA a banker uses.

  find(cik, as_of) -> {"ltm_adj_ebitda": {value, quote, ...}, "as_converted_shares": {value, quote}, "source": {...}} or None

What is read, each with the sentence or table row it came from:
  ltm_adj_ebitda       trailing-twelve-month Adjusted EBITDA as the release states it (the leverage disclosure usually does)
  as_converted_shares  fully diluted shares "on an as-converted basis" (an Up-C: Class A plus units exchangeable 1:1),
                       in millions
The parsers take text, so the tests run them without the network."""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(1, str(Path(__file__).resolve().parent.parent))

LTM = [r"trailing[- ]twelve[- ]months?\s+Adjusted EBITDA (?:of|was|totaled|totalled)\s+(?:approximately\s+)?\$\s?(\d[\d,]*(?:\.\d+)?)\s*(million|billion)",
       r"(?:Last|Trailing) (?:52[- ]Weeks?|Twelve[- ]Months?|12[- ]Months?) Adjusted EBITDA\s*\|\s*\$?\s?(\d[\d,]*(?:\.\d+)?)()",
       r"(?:LTM|TTM) Adjusted EBITDA (?:of|was)\s+\$\s?(\d[\d,]*(?:\.\d+)?)\s*(million|billion)"]
SHARES = r"(?im)^\|\s*(?:Fully )?Diluted Shares[^|]{0,40}as[- ]converted basis[^|]{0,20}\|\s*(\d[\d,]*(?:\.\d+)?)\s*\|"

def parse(text):
    out = {}
    for rx in LTM:
        m = re.search(rx, text, re.I)
        if m:
            v = float(m.group(1).replace(",", "")) * (1000 if (m.group(2) or "").lower() == "billion" else 1)
            out["ltm_adj_ebitda"] = {"value": v, "quote": re.sub(r"\s+", " ", m.group(0))[:240]}; break
    m = re.search(SHARES, text)
    if m: out["as_converted_shares"] = {"value": float(m.group(1).replace(",", "")), "quote": re.sub(r"\s+", " ", m.group(0)).strip()[:200]}
    return out

def releases(cik, as_of, n=3):
    """The n latest 8-K filings with Item 2.02 filed on or before as_of: [(filed, accession, primary document)]."""
    from common import sec_json
    sub = sec_json(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json"); r = sub["filings"]["recent"]
    rows = [(d, a, doc) for f, d, a, doc, it in zip(r["form"], r["filingDate"], r["accessionNumber"], r["primaryDocument"], r.get("items", [""] * len(r["form"])))
            if f == "8-K" and "2.02" in (it or "") and (not as_of or d <= as_of)]
    return sorted(rows, reverse=True)[:n]

def find(cik, as_of, log=print):
    from common import sec_json, get, sec_ua
    from edgar_precedents import html_to_text
    for filed, acc, primary in releases(cik, as_of):
        base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}"
        try: idx = sec_json(f"{base}/index.json")
        except Exception as e: log(f"  earnings release {acc}: {e}"); continue
        docs = [i["name"] for i in idx["directory"]["item"] if i["name"].lower().endswith((".htm", ".html")) and i["name"] != primary and not re.match(r"R\d+\.htm", i["name"])]
        docs.sort(key=lambda n: (0 if re.search(r"ex-?99|press|release|earning", n, re.I) else 1, n))
        for doc in docs[:4]:
            try: text = html_to_text(get(f"{base}/{doc}", headers={"User-Agent": sec_ua()}).text)
            except Exception as e: log(f"  {doc}: {e}"); continue
            got = parse(text)
            if got.get("ltm_adj_ebitda"):
                got["source"] = {"form": "8-K (Item 2.02)", "accn": acc, "doc": doc, "filed": filed, "url": f"{base}/{doc}"}
                return got
    return None
