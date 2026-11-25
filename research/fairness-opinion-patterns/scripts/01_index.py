"""Build an index of merger filings that contain a DCF fairness analysis, via EDGAR full-text search (2001+)."""
import requests, time, json, sys
UA = {"User-Agent": "fo-research-project contact@example.org"}
QUERIES = ['"discounted cash flow" "discount rates ranging"', '"discounted cash flow" "weighted average cost of capital"',
           '"discounted cash flow" "discount rates of"', '"discounted cash flow" "perpetuity growth"', '"discounted cash flow" "terminal multiple"']
FORMS = ["DEFM14A", "SC 14D9", "DEFM14C", "SC 13E3", "SC TO-T"]
out = {}
def get(params):
    for a in range(6):
        try:
            r = requests.get("https://efts.sec.gov/LATEST/search-index", params=params, headers=UA, timeout=60)
            if r.status_code == 200: return r.json()
            time.sleep(3 * (a + 1))
        except Exception as e: time.sleep(3 * (a + 1))
    return None
for form in FORMS:
    for q in QUERIES:
        for yr in range(2001, 2027):
            frm = 0
            while True:
                j = get({"q": q, "forms": form, "dateRange": "custom", "startdt": f"{yr}-01-01", "enddt": f"{yr}-12-31", "from": frm})
                time.sleep(0.15)
                if not j: break
                hs = j["hits"]["hits"]; tot = j["hits"]["total"]["value"]
                for h in hs:
                    s = h["_source"]; acc, doc = h["_id"].split(":", 1)
                    key = acc + ":" + doc
                    if key not in out:
                        out[key] = {"acc": acc, "doc": doc, "form": s.get("form"), "root_form": s.get("root_forms"), "date": s.get("file_date"),
                                    "names": s.get("display_names", []), "ciks": s.get("ciks", []), "sics": s.get("sics", []), "file_type": s.get("file_type"),
                                    "file_desc": s.get("file_description"), "q": []}
                    out[key]["q"].append(q)
                frm += len(hs)
                if len(hs) == 0 or frm >= tot or frm >= 9900: break
            print(form, q[:40], yr, len(out), flush=True)
json.dump(out, open("data/index.json", "w"))
print("total", len(out))
