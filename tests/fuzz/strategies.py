"""Hypothesis strategies for the inputs the pipeline reads: proxy and board-book text, EDGAR HTML tables with the fragments
EDGAR really produces, and financial figures in every form a filing writes them."""
from hypothesis import strategies as st

# words that carry meaning for the classifiers, mixed with noise, so random text actually exercises the regexes
VOCAB = ["Opinion of", "William Blair", "Goldman Sachs", "discounted cash flow", "selected public companies", "precedent transactions",
         "premiums paid", "52-week", "price targets", "leveraged buyout", "sum-of-the-parts", "Rule 13e-3", "Special Committee",
         "for reference only", "Certain Unaudited Prospective Financial Information", "Interests of the Company's Directors", "General",
         "the Company", "Merger", "(the “Merger”)", "(“Parent”)", "analysis", "implied", "per share", "|", "-----PAGE-----", "\n", "\n\n", ".", ",", "?"]

def financial_figure():
    """A figure as a proxy writes it: $35.00, $(1,234.5), (0.7)%, 9.1x, 12.5%, NM, n.a., —, with optional footnote marker."""
    num = st.builds(lambda i, d: f"{i:,}" + (f".{d}" if d else ""), st.integers(0, 99_999), st.sampled_from(["", "0", "5", "00", "25", "1"]))
    form = st.sampled_from(["{n}", "${n}", "$({n})", "({n})", "{n}%", "({n})%", "{n}x", "${n}x"])
    plain = st.builds(lambda f, n: f.format(n=n), form, num)
    return st.one_of(plain, st.sampled_from(["NM", "n.m.", "n.a.", "NA", "—", "-"]))

def edgar_fragments(fig):
    """How EDGAR splits one figure across cells: '$' | '273', '(0.7' | '%)', '9.1' | 'x', with empty spacer cells around."""
    if fig.startswith("$(") and fig.endswith(")"): return ["$(", fig[2:-1], ")"]
    if fig.startswith("$"): return ["$", fig[1:]]
    if fig.endswith(")%"): return [fig[:-2], ")%"]
    if fig.endswith("%"): return [fig[:-1], "%"]
    if fig.endswith("x") and fig[:-1][-1:].isdigit(): return [fig[:-1], "x"]
    return [fig]

text_soup = st.lists(st.one_of(st.sampled_from(VOCAB), st.text(min_size=0, max_size=12), financial_figure()), max_size=80).map(" ".join)

label = st.text(alphabet=st.characters(whitelist_categories=("Lu", "Ll"), max_codepoint=0x7f), min_size=3, max_size=14).map(lambda s: s.capitalize() + " Inc.")
