#!/usr/bin/env python3
"""Stage 4 of the ticker-to-proxy lifecycle: the fairness opinion letter, in the standard form of a filed opinion annex.

  python3 build_letter.py <company.json> <deal_terms.json> <valuation.json> <deck.json> <out dir> [--force]
      writes opinion_letter.txt, opinion_letter.docx and letter.json

The letter names the documents reviewed and the analyses performed exactly as the board book presents them (deck.json), so
the proxy drafter downstream sees one consistent story: model -> book -> letter. Before writing, it compares the offer price
with the low end of each valuation range. An advisor would not render the opinion when the price sits below the low end of
most analyses, so the stage stops there unless --force is given; letter.json records the comparison either way.
Unknowns a real letter would state (merger sub, agreement date, fee terms, relationships) are left as [bracketed] reviewer
markers, never invented."""
import sys, re, shutil, subprocess, datetime, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load, save, need, SCHEMAS, disclaimer, STATES

NAMES = {"dcf": "a discounted cash flow analysis", "comps": "a selected public companies analysis", "lbo": "a leveraged buyout analysis", "premiums": "a premiums paid analysis",
         "trading_range": "the 52-week trading range of the Company Common Stock", "sensitivity": None}
CORE = ("comps", "dcf_pgr", "dcf_exit", "lbo", "premiums")

def support(val, offer):
    rows = []
    for k in CORE:
        lo, hi = val["ranges"][k]["low"], val["ranges"][k]["high"]
        rows.append({"analysis": k, "low": lo, "high": hi, "offer_vs_range": "above" if offer > hi else ("within" if offer >= lo else "below")})
    ok = sum(r["offer_vs_range"] != "below" for r in rows)
    return rows, ok >= (len(rows) + 1) // 2

def letter_text(co, terms, val, deck):
    t = co["target"]; date = datetime.date.fromisoformat(terms["opinion_date"]).strftime("%B %-d, %Y"); offer = terms["offer_price"]
    regime13 = terms["regime"] == "13e-3"
    addressee = terms["addressee"]; addr_block = (addressee[4:] if addressee.lower().startswith("the ") else addressee)
    holders = "the holders of the outstanding shares of common stock of the Company (other than the Excluded Holders)" if regime13 else "the holders of the outstanding shares of common stock of the Company (other than the Excluded Shares)"
    analyses = [NAMES[a] for a in ("dcf", "comps", "lbo", "premiums", "trading_range") if a in deck["analyses"] and NAMES.get(a)]
    st = STATES.get(t.get("state_of_incorporation") or "", t.get("state_of_incorporation") or "[state]")
    P = []
    P.append(date)
    P.append(f"{addr_block[0].upper() + addr_block[1:]}\n{t['name']}\n[Address]")
    P.append("Members of the " + ("Special Committee:" if "committee" in addressee.lower() else "Board:"))
    P.append(f"We understand that {t['name']}, a {st} corporation (the “Company”), proposes to enter into an Agreement and Plan of Merger, dated as of [agreement date] (the “Agreement”), "
             f"by and among {terms['buyer']} (“Parent”), [Merger Sub], a wholly owned subsidiary of Parent (“Merger Sub”), and the Company, pursuant to which, among other things, "
             f"Merger Sub will merge with and into the Company (the “Merger”) and each outstanding share of common stock of the Company (the “Company Common Stock”), other than "
             f"{'shares held by Parent, Merger Sub, the Rollover Holders and their respective affiliates (the “Excluded Holders”)' if regime13 else 'shares held by Parent, Merger Sub or the Company and dissenting shares (the “Excluded Shares”)'}, "
             f"will be converted into the right to receive ${offer:,.2f} in cash, without interest (the “Merger Consideration”). The terms and conditions of the Merger are more fully set forth in the Agreement.")
    P.append(f"You have requested our opinion as to the fairness, from a financial point of view, to {holders} of the Merger Consideration to be received by such holders pursuant to the Agreement.")
    P.append("In connection with preparing our opinion, we have, among other things:")
    yrs = sorted({r["fy"] for r in t.get("annual", [])})
    items = ["reviewed a draft of the Agreement dated [draft date], which we have assumed does not differ in any respect material to our analysis from the Agreement as executed;",
             f"reviewed certain publicly available business and financial information relating to the Company, including its Annual Reports on Form 10-K for the fiscal years {yrs[0] if yrs else '[year]'} through {yrs[-1] if yrs else '[year]'} and its most recent Quarterly Report on Form 10-Q;",
             "reviewed certain illustrative financial projections for the Company for the fiscal years " + (f"{yrs[-1] + 1} through {yrs[-1] + 5}" if yrs else "[years]") + ", derived from the Company’s publicly reported financial results (the “Projections”);",
             "reviewed the reported prices and trading activity of the Company Common Stock;",
             "compared the financial performance of the Company and the prices and trading activity of the Company Common Stock with those of certain other publicly traded companies that we deemed relevant;"]
    items += [f"performed {a};" for a in analyses]
    items.append("performed such other financial studies and analyses and considered such other information and factors as we deemed appropriate.")
    for i, it in enumerate(items): P.append(f"({roman(i + 1)}) {it}")
    P.append("In arriving at our opinion, we have assumed and relied upon, without independent verification, the accuracy and completeness of all of the financial and other information that was publicly available or furnished or otherwise made available to us, and we have not assumed any responsibility for independently verifying such information. "
             "With respect to the Projections, we have assumed that they have been reasonably prepared on bases reflecting the best currently available estimates and judgments as to the future financial performance of the Company, and we express no view as to the Projections or the assumptions on which they are based. "
             "We have not made any independent valuation or appraisal of the assets or liabilities of the Company, nor have we been furnished with any such valuation or appraisal.")
    P.append("We have assumed that the Merger will be consummated in accordance with the terms set forth in the Agreement, without any waiver, amendment or delay of any terms or conditions that would be material to our analysis, and that all governmental, regulatory and other consents and approvals necessary for the consummation of the Merger will be obtained without any adverse effect on the Company or the Merger that would be material to our analysis.")
    P.append(f"Our opinion is necessarily based on economic, market and other conditions as in effect on, and the information made available to us as of, the date hereof. Subsequent developments may affect this opinion, and we do not have any obligation to update, revise or reaffirm this opinion. "
             f"Our opinion addresses only the fairness, from a financial point of view, as of the date hereof, to {holders} of the Merger Consideration, and does not address any other term or aspect of the Agreement or the Merger, the relative merits of the Merger as compared to any alternative transaction, or the underlying business decision of the Company to engage in the Merger. "
             "We express no opinion as to the fairness of the amount or nature of any compensation to any officers, directors or employees of the Company, or any class of such persons, relative to the Merger Consideration. This opinion does not constitute a recommendation to any holder of Company Common Stock as to how such holder should vote or act with respect to the Merger or any other matter.")
    P.append(f"We have acted as financial advisor to {addressee} in connection with the Merger and will receive a fee for our services, [a portion of which is payable upon delivery of this opinion and the principal portion of which is contingent upon consummation of the Merger] [reviewer: fee terms from the engagement letter]. "
             "In addition, the Company has agreed to reimburse certain of our expenses and to indemnify us for certain liabilities that may arise out of our engagement. [Reviewer: prior and current relationships with the Company, Parent and their affiliates, and fees received, from the advisor’s relationship disclosure memo.]")
    P.append(f"This letter is provided for the information of {addressee} (in its capacity as such) in connection with and for the purposes of its evaluation of the Merger. This opinion has been approved by a fairness committee of [the advisor] in accordance with its customary practice.")
    P.append(f"Based upon and subject to the foregoing, it is our opinion that, as of the date hereof, the Merger Consideration to be received by {holders} pursuant to the Agreement is fair, from a financial point of view, to such holders.")
    P.append(f"Very truly yours,\n\n{terms['advisor'].upper()}")
    return P

def roman(n):
    out = ""
    for v, s in ((10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")):
        while n >= v: out += s; n -= v
    return out

def run(company_json, terms_json, valuation_json, deck_json, out, force=False, log=print):
    co = need(load(company_json), "company", company_json); terms = need(load(terms_json), "deal_terms", terms_json)
    val = need(load(valuation_json), "valuation", valuation_json); deck = need(load(deck_json), "deck", deck_json)
    rows, supported = support(val, terms["offer_price"])
    for r in rows: log(f"  {r['analysis']:9s} {r['low']:8.2f} - {r['high']:8.2f}  offer {terms['offer_price']:.2f} {r['offer_vs_range']}")
    meta = {"schema": SCHEMAS["letter"], "offer_vs_ranges": rows, "supported": supported, "forced": bool(force and not supported)}
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    if not supported and not force:
        meta["written"] = False; save(meta, out / "letter.json")
        raise SystemExit(f"the offer price ${terms['offer_price']:,.2f} is below the low end of most valuation ranges; an advisor would not render a fairness opinion at this price. "
                         "Raise the premium (--premium) or offer price, revisit the assumptions in the model, or pass --force to write the letter anyway.")
    P = letter_text(co, terms, val, deck)
    head = disclaimer(terms["advisor"], co["target"]["name"])
    txt = head + "\n\n" + "\n\n".join(P) + "\n"; tp = out / "opinion_letter.txt"; tp.write_text(txt); log(f"wrote {tp} ({len(txt.split())} words)")
    try:
        import docx
        from docx.shared import Pt, RGBColor
        doc = docx.Document(); st = doc.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(11)
        h = doc.add_paragraph().add_run(head); h.italic = True; h.font.size = Pt(8); h.font.color.rgb = RGBColor(0xC0, 0, 0)
        for p in P:
            para = doc.add_paragraph()
            for j, line in enumerate(p.split("\n")):
                if j: para.add_run().add_break()
                para.add_run(line)
            if re.match(r"^\([ivx]+\) ", p): para.paragraph_format.left_indent = Pt(36)
        dp = out / "opinion_letter.docx"; doc.save(dp); log(f"wrote {dp}")
    except ImportError: log("python-docx not installed: opinion_letter.docx not written")
    meta.update({"written": True, "txt": str(tp), "words": len(txt.split()), "markers": sorted(set(re.findall(r"\[[^\]]+\]", txt)))}); save(meta, out / "letter.json")
    return meta

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("company"); ap.add_argument("terms"); ap.add_argument("valuation"); ap.add_argument("deck"); ap.add_argument("out"); ap.add_argument("--force", action="store_true"); a = ap.parse_args()
    run(a.company, a.terms, a.valuation, a.deck, a.out, a.force)
