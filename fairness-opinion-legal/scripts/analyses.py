"""Analysis vocabulary shared by the classifier, the shell builder, the self-scorer and the precedent verifier."""
import re
LABELS = ["comps", "precedents", "dcf", "lbo", "premiums", "trading_range", "targets", "future_price", "sotp", "sensitivity", "nav", "ddm"]
VALUATION = {"comps", "precedents", "dcf", "lbo", "premiums", "trading_range", "targets", "future_price", "sotp", "nav", "ddm"}
# how a proxy section names each analysis
ANALYSES = {"comps": r"selected (publicly traded |public |comparable )?compan|comparable compan|trading (comparables|multiples)|peer group", "precedents": r"precedent transaction|selected transaction|comparable transaction|selected m&a|transaction multiples",
            "dcf": r"discounted cash flow|\bdcf\b", "lbo": r"leveraged buyout|\blbo\b|ability to pay|financial sponsor", "premiums": r"premiums? paid|premia", "trading_range": r"52-?week|historical (stock |share )?(trading|price)|trading range|stock price (performance|history)",
            "targets": r"analyst|price target|research (analyst|price)", "future_price": r"future (share|stock) price|present value of (future|implied)|illustrative future|discounted (future|equity)", "sotp": r"sum[- ]of[- ]the[- ]parts",
            "sensitivity": r"analysis at various prices|various (offer |transaction )?prices|sensitivity analys", "nav": r"net asset value|\bnav\b", "ddm": r"dividend discount"}
# how a board-book page titles each analysis
DECK_RX = {"comps": r"(selected|comparable|public|trading) (public(ly)? )?(traded )?compan|trading comparables|peer|comparable compan|trading multiples", "precedents": r"precedent|selected transactions|comparable transactions|m&a transactions|transaction (comparables|multiples)",
           "dcf": r"discounted cash flow|\bdcf\b|unlevered free cash flow", "lbo": r"\blbo\b|leveraged buyout|sponsor (ability|analysis)|ability to pay|financial sponsor", "premiums": r"premiums? paid|premia",
           "trading_range": r"(stock|share) price (performance|history)|trading (history|performance|range)|52-?week|price performance|vwap", "targets": r"analyst|price target|broker|wall street|research",
           "future_price": r"future (share|stock) price|present value of (future|implied)|illustrative future|discounted (future|equity)", "sotp": r"sum[- ]of[- ]the[- ]parts|\bsotp\b", "sensitivity": r"sensitivit|analysis at various prices|various (prices|offer)|illustrative (analysis|value) at",
           "nav": r"net asset value|\bnav\b", "ddm": r"dividend discount"}
# headings inside a filed section, for segmentation
HEAD = [("comps", r"selected (?:public(?:ly)?(?: traded)? |comparable |publicly traded )?compan(?:y|ies)|comparable (?:public )?compan|public (?:company|market) (?:trading )?(?:analysis|comparables)|trading (?:comparables|multiples)"),
        ("precedents", r"precedent transaction|selected (?:precedent )?transaction|comparable transaction|selected m&a|precedent m&a|transaction (?:comparables|multiples)"),
        ("dcf", r"discounted cash flow|\bdcf\b"), ("lbo", r"leveraged buyout|\blbo\b|ability to pay|sponsor"), ("premiums", r"premiums? paid|premia"),
        ("trading_range", r"52-?week|historical (?:stock |share )?(?:trading|price)|trading range|stock price (?:performance|history)|historical trading"),
        ("targets", r"analyst price target|price target|research analyst|wall street"), ("future_price", r"future (?:share|stock) price|present value of (?:future|implied)|illustrative future"),
        ("sotp", r"sum[- ]of[- ]the[- ]parts"), ("nav", r"net asset value|\bnav\b"),
        ("other", r"other (?:factors|considerations|information|analyses|matters)|additional (?:factors|considerations)|^general\b|^miscellaneous")]
NUMERIC = re.compile(r"(?:US|C|A|HK)?\$\s?\d|\d+(?:\.\d+)?\s?%|\d+(?:\.\d+)?x\b", re.I)
REF = re.compile(r"for reference (purposes )?only|for informational purposes|informational purposes only|reference only|informational only|for illustrative purposes", re.I)
def presented(section):
    """Analyses a section presents with a stated result: a mention followed within 900 characters by a dollar amount, a percentage or a multiple."""
    return sorted(k for k, rx in ANALYSES.items() if any(NUMERIC.search(section[m.end(): m.end() + 900]) for m in re.finditer(rx, section, re.I)))
