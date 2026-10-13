import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, tei_year, first_year

h = Harvest("memis-slovenia")
U = "https://www.clarin.si/repository/xmlui/bitstream/handle/11356/1376/MEMIS.xml?sequence=3&isAllowed=y"
raw = h.get(U, "files/MEMIS.xml")
divs = re.split(r'(?=<div type="inscription")', raw)[1:]
und = []
for d in divs:
    d = d.split("</body>")[0]
    n = re.search(r'n="(\d+)"', d).group(1)
    od = re.search(r"<origDate[^>]*>(.*?)</origDate>", d, re.S)
    ds = re.sub(r"\s+", " ", od.group(1)).strip() if od else ""
    if re.match(r"2\. pol\. 15\. stol", ds): y = 1475
    elif re.match(r"1\.-2\. stol|1\. stol", ds): y = 100
    else: y = first_year(ds)
    if y is None: und.append(n)
    parts = re.findall(r'<div type="(?:transcr|trans)">.*?</div>', d, re.S)
    txt = "\n".join(parts)
    txt = re.sub(r"<head>.*?</head>", "", txt, flags=re.S)
    h.add(f"memis_{int(n):03d}.xml", f"<TEI><text><body>{txt}</body></text></TEI>", language="Latin", year=y,
          source=f"MEMIS inscription {n}", url=U)
rep = h.finish(method="Downloaded MEMIS.xml; one record per <div type=inscription>, keeping only the transcription div(s) (expanded Latin text); description, bibliography and Slovenian translation excluded.",
  coverage="All 51 inscriptions; out-of-window ones kept with their year.",
  problems=["Inscriptions dated '2. pol. 15. stol.' given year 1475; '1. stol. po Kr.' etc. given 100.",
            "Undated inscriptions (year=None, dateless_in_window=False): nos. " + ", ".join(und),
            "Inscription 1 is a pseudo-inscription quoted from a printed statute."])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"])
