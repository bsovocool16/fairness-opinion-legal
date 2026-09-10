"""Normalize advisor names to a bank key so that 'Centerview Partners' and 'Centerview Partners LLC' group together."""
import re
ALIAS = {"bofa": "bofa", "bank": "bofa", "merrill": "bofa", "j.p.": "jpmorgan", "jpmorgan": "jpmorgan", "jp": "jpmorgan", "citigroup": "citi", "citi": "citi",
         "duff": "kroll", "kroll": "kroll", "goldman": "goldman", "morgan": "morganstanley", "centerview": "centerview", "moelis": "moelis", "evercore": "evercore",
         "houlihan": "houlihan", "william": "williamblair", "pjt": "pjt", "macquarie": "macquarie", "rothschild": "rothschild", "solomon": "solomon", "pj": "solomon",
         "segal": "segal", "jefferies": "jefferies", "lazard": "lazard", "barclays": "barclays", "piper": "piper", "raymond": "raymondjames", "stifel": "stifel",
         "guggenheim": "guggenheim", "perella": "perella", "qatalyst": "qatalyst", "wells": "wellsfargo", "rbc": "rbc", "td": "td", "bmo": "bmo", "keefe": "kbw",
         "truist": "truist", "needham": "needham", "roth": "roth", "leerink": "leerink", "allen": "allen", "cowen": "cowen", "ubs": "ubs", "deutsche": "deutsche",
         "credit": "creditsuisse", "nomura": "nomura", "mizuho": "mizuho", "hsbc": "hsbc", "scotia": "scotia", "cibc": "cibc", "canaccord": "canaccord"}
def bank_key(name):
    n = (name or "").lower().replace("&amp;", "&").strip()
    first = re.split(r"[ ,]", n)[0] if n else ""
    return ALIAS.get(first, re.sub(r"[^a-z]", "", first) or "unknown")
