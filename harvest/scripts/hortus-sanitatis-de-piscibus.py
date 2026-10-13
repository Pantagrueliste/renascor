import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys; sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
import re
from lxml import html as LH
h = Harvest("hortus-sanitatis-de-piscibus")
B = "https://www.unicaen.fr/puc/sources/depiscibus/"
tdm = h.get(B + "tdm.html", "files/tdm.html")
pages = []
for m in re.finditer(r'href="(consult/hortus_fr/(FR\.hs\.4\.[^"]+)\.html)"', tdm):
    if m.group(1) not in [p[0] for p in pages]:
        pages.append((m.group(1), m.group(2)))
probs = []
KILL = ".//a[contains(@class,'appel_note')]|.//span[contains(@class,'afficheNote')]|.//span[contains(@class,'bibl')]|.//a[contains(@class,'afficheBibl')]|.//span[@class='affichePlus']|.//span[@class='sup']"
def clean(e):
    for bad in e.xpath(KILL):
        if bad.getparent() is not None:
            bad.tail = bad.tail or ""
            bad.drop_tree()
    for bad in e.xpath(".//span[@onmouseover and .//a[contains(@class,'afficheBibl')]]"):
        bad.drop_tree()
    return re.sub(r"\s+", " ", e.text_content()).strip()
for rel, pid in pages:
    page = h.get(B + rel, f"files/{pid}.html")
    t = LH.fromstring(page)
    parts = []
    for e in t.xpath("//div[@id='txt']//h1[@class='titre-chapitre-latin']|//div[@id='txt']//h2[@class='titre-section-latin']|//div[@id='txt']//p[@class='paragraphe-latin']"):
        s = clean(e)
        s = re.sub(r"^\[\d+\]\s*", "", s)
        if s: parts.append(s)
    text = "\n".join(parts)
    if not text:
        probs.append(f"{pid}: no Latin text found"); continue
    h.add(pid + ".txt", text, language="Latin", year=1491, source=f"Hortus sanitatis, liber IV (De piscibus), {pid} (Mainz, Meydenbach, 1491)", url=B + rel)
probs.append("Latin text only (paragraphe-latin and Latin headings); French translation, notes, apparatus popups and bibliographic source labels/quotations removed. Chapter headings: the Latin heading may contain a list of names. Online edition is a modern critical text of the 1491 print (editorial variants resolved in apparatus, which was dropped).")
rep = h.finish(method="No bulk export (the 'sourcesXML' link returns 404); crawled the 108 chapter pages listed in tdm.html.", coverage="All pages of the table of contents (prologue and chapters of Book IV).", problems=probs)
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"])
