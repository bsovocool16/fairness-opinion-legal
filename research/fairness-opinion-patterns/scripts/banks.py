import re
BANKS = [  # (key, display, regex)
 ("goldman","Goldman Sachs",r"Goldman,? Sachs"), ("morganstanley","Morgan Stanley",r"Morgan Stanley"), ("jpmorgan","J.P. Morgan",r"J\.\s?P\.\s?Morgan|JPMorgan|JP Morgan"),
 ("bofa","BofA / Merrill Lynch",r"BofA Securities|BofA Merrill|Merrill Lynch|Banc of America Securities|Merrill"), ("citi","Citi",r"Citigroup Global|Citigroup|Salomon Smith Barney|\bCiti\b"),
 ("creditsuisse","Credit Suisse",r"Credit Suisse|First Boston|DLJ|Donaldson,? Lufkin"), ("lazard","Lazard",r"Lazard"), ("evercore","Evercore",r"Evercore"), ("centerview","Centerview",r"Centerview"),
 ("moelis","Moelis",r"Moelis"), ("pjt","PJT Partners",r"PJT Partners|\bPJT\b"), ("perella","Perella Weinberg",r"Perella Weinberg|\bPWP\b"), ("qatalyst","Qatalyst",r"Qatalyst"),
 ("guggenheim","Guggenheim",r"Guggenheim"), ("jefferies","Jefferies",r"Jefferies"), ("houlihan","Houlihan Lokey",r"Houlihan Lokey|Houlihan|\bHLHZ"), ("barclays","Barclays",r"Barclays"), ("lehman","Lehman Brothers",r"Lehman Brothers|\bLehman\b"), ("cibc","CIBC",r"\bCIBC\b"), ("robertsonstephens","Robertson Stephens",r"Robertson Stephens"), ("mcdonald","McDonald / KeyBanc",r"McDonald Investments"), ("leggmason","Legg Mason",r"Legg Mason"), ("abnamro","ABN AMRO",r"ABN AMRO"), ("dresdner","Dresdner Kleinwort",r"Dresdner|Kleinwort"), ("capitalink","Capitalink",r"Capitalink"), ("adamsharkness","Adams Harkness",r"Adams,? Harkness"), ("wrhambrecht","WR Hambrecht",r"Hambrecht"), ("sunrise","Sun Trust",r"Sun Trust"), ("seidman","Seidman",r"Seidman"), ("southard","Southard",r"Southard"),
 ("ubs","UBS",r"\bUBS\b"), ("deutsche","Deutsche Bank",r"Deutsche Bank|Deutsche Banc|\bDBAB\b|\bDBSI\b"), ("wellsfargo","Wells Fargo",r"Wells Fargo|Wachovia"), ("rbc","RBC",r"RBC Capital|\bRBC\b"),
 ("kroll","Duff & Phelps / Kroll",r"Duff\s*&\s*Phelps|Kroll"), ("williamblair","William Blair",r"William Blair"), ("piper","Piper Sandler",r"Piper Sandler|Piper Jaffray|\bPiper\b"),
 ("raymondjames","Raymond James",r"Raymond James"), ("stifel","Stifel / KBW",r"Stifel|Keefe,? Bruyette|\bKBW\b"), ("sandler","Sandler O'Neill",r"Sandler O.Neill"), ("greenhill","Greenhill",r"Greenhill"),
 ("allen","Allen & Co",r"Allen\s*&\s*Company"), ("rothschild","Rothschild",r"Rothschild"), ("macquarie","Macquarie",r"Macquarie"), ("cowen","TD Cowen",r"Cowen"),
 ("needham","Needham",r"Needham"), ("baird","Baird",r"Robert W\. Baird|\bBaird\b"), ("bmo","BMO",r"BMO Capital"), ("keybanc","KeyBanc",r"KeyBanc"), ("truist","Truist / SunTrust",r"Truist|SunTrust Robinson"),
 ("bearstearns","Bear Stearns",r"Bear,? Stearns"), ("blackstone","Blackstone",r"Blackstone Advisory|Blackstone Group L\.P\.|The Blackstone Group"), ("oppenheimer","Oppenheimer",r"Oppenheimer"),
 ("leerink","Leerink / SVB",r"Leerink|SVB Securities"), ("canaccord","Canaccord",r"Canaccord"), ("tudor","Tudor Pickering",r"Tudor,? Pickering"), ("solomon","Solomon Partners",r"Solomon Partners|PJ Solomon|Peter J\. Solomon"),
 ("stephens","Stephens",r"Stephens Inc"), ("janney","Janney",r"Janney"), ("bbandt","BB&T Capital",r"BB&T Capital"), ("thomasweisel","Thomas Weisel",r"Thomas Weisel"), ("fbr","FBR",r"\bFBR\b|Friedman,? Billings"),
 ("cantor","Cantor Fitzgerald",r"Cantor Fitzgerald"), ("ducera","Ducera",r"Ducera"), ("lincoln","Lincoln International",r"Lincoln International"), ("stout","Stout",r"\bStout\b"), ("marshallstevens","Marshall & Stevens",r"Marshall\s*&\s*Stevens"),
 ("ladenburg","Ladenburg",r"Ladenburg"), ("broadpoint","B. Riley",r"B\. Riley"), ("roth","Roth",r"Roth Capital"), ("craighallum","Craig-Hallum",r"Craig-Hallum"), ("simmons","Simmons",r"Simmons\s*&\s*Company"),
 ("scotia","Scotiabank",r"Scotia Capital|Scotiabank"), ("tdsec","TD Securities",r"TD Securities"), ("mizuho","Mizuho",r"Mizuho"), ("nomura","Nomura",r"Nomura"), ("hsbc","HSBC",r"\bHSBC\b"), ("bnp","BNP Paribas",r"BNP Paribas"),
 ("sterne","Sterne Agee",r"Sterne Agee"), ("morgankeegan","Morgan Keegan",r"Morgan Keegan"), ("dahlman","Dahlman Rose",r"Dahlman Rose"), ("cohen","Cohen & Company",r"Cohen\s*&\s*Company"),
 ("kpmg","KPMG",r"\bKPMG\b"), ("bdo","BDO",r"\bBDO\b"), ("vrc","Valuation Research",r"Valuation Research"), ("gordian","Gordian",r"Gordian"), ("loopcap","Loop Capital",r"Loop Capital"),
 ("ewing","Ewing Bemiss",r"Ewing Bemiss"), ("mlv","Hovde",r"Hovde"), ("boenning","Boenning",r"Boenning"), ("feldman","Feldman Financial",r"Feldman Financial"), ("rpfin","RP Financial",r"RP Financial"),
 ("dadavidson","D.A. Davidson",r"D\.\s?A\. Davidson"), ("ps","Panmure",r"Panmure"), ("alvarez","Alvarez & Marsal",r"Alvarez\s*&\s*Marsal"), ("tailwater","Tegris",r"Tegris"),
]
BANK_RX = [(k, d, re.compile(r)) for k, d, r in BANKS]
DISPLAY = {k: d for k, d, _ in BANKS}
TIER = {k: "bulge" for k in ["goldman","morganstanley","jpmorgan","bofa","citi","creditsuisse","barclays","lehman","ubs","deutsche","wellsfargo","bearstearns","rbc","mizuho","nomura","hsbc","bnp"]}
TIER.update({k: "elite boutique" for k in ["lazard","evercore","centerview","moelis","pjt","perella","qatalyst","guggenheim","greenhill","allen","rothschild","blackstone","solomon","ducera"]})
TIER.update({k: "valuation firm" for k in ["kroll","houlihan","stout","marshallstevens","vrc","lincoln","kpmg","bdo","gordian","alvarez","feldman","rpfin"]})
def first_bank(s):
    best = None
    for k, d, rx in BANK_RX:
        m = rx.search(s)
        if m and (best is None or m.start() < best[1]): best = (k, m.start())
    return best[0] if best else None
