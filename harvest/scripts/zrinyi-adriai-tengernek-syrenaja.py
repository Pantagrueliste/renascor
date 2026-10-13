import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
from bs4 import BeautifulSoup
h = Harvest("zrinyi-adriai-tengernek-syrenaja")
B = "https://magyar-irodalom.elte.hu/gepesk/zrinyi/"
def page(u, rel):
    b = h.get(u, rel, binary=True)
    return b.decode("cp1250", errors="replace")
def text(html):
    s = BeautifulSoup(html, "html.parser")
    for t in s(["script", "style"]): t.decompose()
    return re.sub(r"[ \t\r\f\v]+", " ", s.get_text("\n")).strip()
for key, d, label, src in (("syrena", "syrena/", "Syrena manuscript", "Syrena codex"), ("1651", "1651/", "1651 print", "1651 Vienna print")):
    toc = page(B + d + "tartalom.htm", f"files/{key}/tartalom.htm")
    links = re.findall(r'HREF="([^"]+\.htm)"', toc, re.I)
    parts = []
    for l in links:
        parts.append(text(page(B + d + l, f"files/{key}/{l}")))
    h.add(f"zrinyi_{key}.txt", "\n\n".join(parts), language="Hungarian", year=1651, source="Zrínyi: Adriai tengernek syrénája, " + label,
          url=B + d + "tartalom.htm")
rep = h.finish(method="Crawled the two content lists (syrena/tartalom.htm, 1651/tartalom.htm) and every linked old-spelling HTML page (cp1250); text of the pages concatenated into one record per witness.",
  coverage="All 22 manuscript pages and 21 print pages.",
  problems=["No robots.txt on the host (returns an error page)","Syrena manuscript is not separately dated on the site: year set to 1651 (date of the print / work), as in the catalogue period","Pages may include a few editorial page/folio marks"])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"])
