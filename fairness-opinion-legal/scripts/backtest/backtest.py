#!/usr/bin/env python3
"""Backtest the ticker-to-proxy pipeline against a held-out deal: run it blind as of the pre-announcement date, then compare
each stage with the filed record. Protocol and metrics: references/backtest.md.

  python3 backtest.py blind <spec.json> <bt dir> [--precedents]   point-in-time run of the lifecycle into <bt>/blind/
  python3 backtest.py seal  <spec.json> <bt dir>                  fetch the filed record into <bt>/sealed/ and parse truth.json
  python3 backtest.py audit <spec.json> <bt dir>                  leakage checks on <bt>/blind/; writes audit.json
  python3 backtest.py score <spec.json> <bt dir>                  scorecard.json and scorecard.md
  python3 backtest.py all   <spec.json> <bt dir> [--precedents]   blind, seal, audit, score

The spec (examples/backtest/*.json) holds only what was known at signing (ticker, CIK, advisor, buyer, offer price, regime,
opinion and unaffected dates, the data cutoff) plus where the filed record is on EDGAR. `blind` reads nothing under sealed/,
and `seal` runs after `blind` in `all`, so a bug cannot route the record into the run.
"""
import os, re, sys, json, argparse, subprocess, datetime
from pathlib import Path
HERE = Path(__file__).resolve().parent; SCRIPTS = HERE.parent; PLUGIN = SCRIPTS.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(SCRIPTS))

def load_spec(p):
    spec = json.loads(Path(p).read_text()); spec["_dir"] = str(Path(p).resolve().parent)
    for k in ("id", "ticker", "cik", "advisor", "bank", "buyer", "buyer_type", "regime", "offer_price", "opinion_date", "unaffected_date", "cutoff", "record"):
        if k not in spec: raise SystemExit(f"spec {p} lacks {k}")
    if spec["cutoff"] > spec["opinion_date"]: raise SystemExit("cutoff after the opinion date: the advisor could not have seen that data")
    return spec

def blind(spec, bt, precedents=False, price_cache=None, assisted=False):
    """The lifecycle as of the cutoff, with the deal's real signing terms, into <bt>/blind/. Auto mode takes no judgment input;
    assisted mode adds the spec's `assisted` inputs (peers), each of which must cite a source filed before the cutoff."""
    out = Path(bt) / "blind"; out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    pc = price_cache or spec.get("price_cache")
    if pc:
        pc = Path(pc) if Path(pc).is_absolute() else Path(spec["_dir"]) / pc
        if pc.exists(): env["PRICE_CACHE"] = str(pc)
        else: print(f"price cache {pc} not found; prices come from the network (a delisted ticker will fail)")
    cmd = [sys.executable, str(SCRIPTS / "lifecycle" / "ticker_to_proxy.py"), "run", spec["ticker"], str(out), "--advisor", spec["advisor"],
           "--buyer", spec["buyer"], "--buyer-type", spec["buyer_type"], "--offer-price", str(spec["offer_price"]), "--regime", spec["regime"],
           "--opinion-date", spec["opinion_date"], "--unaffected-date", spec["unaffected_date"], "--as-of", spec["cutoff"], "--cik", str(spec["cik"])]
    for k, flag in (("addressee", "--addressee"), ("codename", "--codename")):
        if spec.get(k): cmd += [flag, spec[k]]
    if assisted:
        A = spec.get("assisted") or {}
        if not A: raise SystemExit("--assisted: the spec has no `assisted` block")
        for k, v in A.items():
            if (v.get("source_filed") or "9999") > spec["cutoff"]: raise SystemExit(f"assisted input {k} cites a source filed {v.get('source_filed')}, after the cutoff")
        if A.get("peers"): cmd += ["--peers", ",".join(A["peers"]["tickers"])]
    if spec.get("force_letter", True): cmd.append("--force")      # the letter must be written even when our ranges disagree; that is a result
    print("$", " ".join(cmd)); r = subprocess.run(cmd, env=env)
    if precedents and r.returncode == 0:
        import precedent_search
        da = json.loads((out / "deck_analyses.json").read_text())["deck_analyses"]
        res = precedent_search.find_precedents(spec["bank"], sorted(da), before=spec["opinion_date"], out_dir=out / "precedents", regime=spec["regime"])
        (out / "precedents" / "results.json").write_text(json.dumps(res, indent=1))
    (out / "blind_run.json").write_text(json.dumps({"cutoff": spec["cutoff"], "at": datetime.datetime.now().isoformat(timespec="seconds"), "returncode": r.returncode, "mode": "assisted" if assisted else "auto", "cmd": cmd[1:]}, indent=1))
    return r.returncode

def walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items(): yield from walk(v, f"{path}.{k}" if path else k)
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from walk(v, f"{path}[{i}]")
    else: yield path, o

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")
def audit(spec, bt):
    """Leakage checks. A failure means the blind run saw something dated after the cutoff or taken from the record."""
    bt = Path(bt); B = bt / "blind"; cut = spec["cutoff"]; fail, warn = [], []
    co = json.loads((B / "lifecycle" / "company.json").read_text()) if (B / "lifecycle" / "company.json").exists() else None
    if not co: fail.append("no blind/lifecycle/company.json")
    else:
        if co.get("as_of") != cut: fail.append(f"company.json as_of {co.get('as_of')} is not the cutoff {cut}")
        for path, v in walk(co):
            leaf = path.rsplit(".", 1)[-1]
            if leaf == "filed" and isinstance(v, str) and v > cut: fail.append(f"company.json {path} filed {v}, after the cutoff")
            if leaf in ("date", "as_of") and isinstance(v, str) and DATE.match(v) and v > cut: fail.append(f"company.json {path} = {v}, after the cutoff")
        for who in [co["target"]] + co.get("peers", []):
            h = (who.get("price") or {}).get("history_1y") or []
            if h and h[-1][0] > cut: fail.append(f"{who.get('ticker')} price history runs to {h[-1][0]}")
        rf = (co.get("market") or {}).get("risk_free") or {}
        if (rf.get("date") or "") > cut: fail.append(f"risk-free rate dated {rf.get('date')}")
        warn.append("peer candidates come from today's SEC ticker list: a peer delisted since the cutoff cannot be picked (survivorship); peers listed after it have no history and drop out")
    terms = B / "lifecycle" / "deal_terms.json"
    if terms.exists():
        t = json.loads(terms.read_text())
        if t.get("unaffected_date") != spec["unaffected_date"]: warn.append(f"unaffected date {t.get('unaffected_date')} differs from the spec's {spec['unaffected_date']}")
    own = {spec["record"][k]["acc"] for k in spec["record"] if isinstance(spec["record"][k], dict) and spec["record"][k].get("acc")}
    for fp in B.rglob("*.json"):
        try: j = json.loads(fp.read_text())
        except Exception: continue
        recs = j if isinstance(j, list) else j.get("verified", []) if isinstance(j, dict) else []
        for r in recs if isinstance(recs, list) else []:
            if isinstance(r, dict) and r.get("acc"):
                if r["acc"] in own: fail.append(f"{fp.name}: precedent {r['acc']} is the deal's own filing")
                if (r.get("date") or "") >= spec["opinion_date"]: fail.append(f"{fp.name}: precedent {r['acc']} dated {r.get('date')}, not before the opinion")
    blob = "\n".join(p.read_text(errors="ignore") for p in B.rglob("*") if p.is_file() and p.suffix in (".txt", ".json", ".md"))
    for acc in own:
        if acc in blob: fail.append(f"the record's accession {acc} appears in the blind run")
    truth = bt / "sealed" / "truth.json"
    if truth.exists():                        # the advisor's own ranges showing up verbatim in our outputs would be a leak
        T = json.loads(truth.read_text())
        own_txt = "\n".join(p.read_text(errors="ignore") for p in B.rglob("*.txt") if "precedents" not in p.parts)
        for k, a in T["section"]["analyses"].items():
            r = a.get("range")
            if r and re.search(rf"\${r['low']:.2f}\D{{1,12}}\${r['high']:.2f}", own_txt): fail.append(f"the filed {k} range ${r['low']:.2f}-${r['high']:.2f} appears in the blind outputs")
    tc = spec.get("drafter_training_cutoff"); ann = spec.get("announced")
    if tc and ann and ann <= tc: warn.append(f"the deal was announced {ann}, on or before the drafter's training cutoff {tc}: the filed section may be memorized")
    if not tc: warn.append("spec gives no drafter_training_cutoff: memorization of the filed record by the drafter is not ruled out")
    res = {"cutoff": cut, "passed": not fail, "failures": fail, "warnings": warn}
    (bt / "audit.json").write_text(json.dumps(res, indent=1)); return res

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["blind", "seal", "audit", "score", "all"]); ap.add_argument("spec"); ap.add_argument("bt")
    ap.add_argument("--precedents", action="store_true", help="also run the precedent search (before the opinion date) on the blind deal folder")
    ap.add_argument("--assisted", action="store_true", help="add the spec's pre-cutoff judgment inputs (peers)")
    ap.add_argument("--price-cache", help="directory of yahoo_<SYMBOL>*.json chart files (overrides the spec's price_cache)")
    a = ap.parse_args(); spec = load_spec(a.spec)
    import record, score
    if a.cmd in ("blind", "all"):
        rc = blind(spec, a.bt, a.precedents, a.price_cache, a.assisted)
        if rc: print(f"blind run stopped (exit {rc}); see {Path(a.bt) / 'blind' / 'lifecycle' / 'manifest.json'}")
    if a.cmd in ("seal", "all"): record.fetch(spec, a.bt)
    if a.cmd in ("audit", "all"):
        r = audit(spec, a.bt); print(f"audit: {'passed' if r['passed'] else 'FAILED'}"); [print("  FAIL", x) for x in r["failures"]]; [print("  warn", x) for x in r["warnings"]]
    if a.cmd in ("score", "all"):
        score.score(spec, a.bt); print((Path(a.bt) / "scorecard.md").read_text())
