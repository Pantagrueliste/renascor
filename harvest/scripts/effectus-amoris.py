import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, html
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
h = Harvest("effectus-amoris")
U = "https://magyar-irodalom.elte.hu/effectus/masodik/3atir.htm"
t = h.get(U, "files/3atir.htm", binary=True).decode("cp1250", errors="replace")
i = t.upper().find("<HR")
body = t[i:]
body = re.sub(r"<A [^>]*>.*?</A>", "", body, flags=re.S | re.I)   # footnote markers
body = re.sub(r"<BR\s*/?>|</P>|</PRE>", "\n", body, flags=re.I)
body = html.unescape(re.sub(r"<[^>]+>", "", body)).replace("\xa0", " ")
lines = []
for l in body.split("\n"):
    l = re.sub(r"^\s*\d{1,3}\s{2,}", "", l)   # line numbers
    l = re.sub(r"\s+", " ", l).strip()
    if l: lines.append(l)
txt = "\n".join(lines)
h.add("effectus-amoris_betuhiv.txt", txt, language="Hungarian", year=1588, source="Effectus Amoris (letter-faithful critical transcription of the Debrecen print 1587-1588)", url=U)
print(h.finish(method="Frame chain index -> 2almenu -> 2atirfr -> 3atir.htm (Betuhiv kritikai szoveg, cp1250). Kept only the letter-faithful transcription; dropped the pronunciation-oriented and modern-language versions, the editorial note, footnote markers and line numbers.",
 coverage="Whole poem (letter-faithful version) harvested; footnotes (3atirj.htm), other versions and photographs excluded.",
 problems=["Year 1588 = imprint date on the print (title page 1587, colophon Debrecen 1588); both in window.", "Text contains a short Latin argument and commonplace (main language Hungarian)."]))
