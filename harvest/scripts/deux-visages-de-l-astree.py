import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR + "")
from bs4 import BeautifulSoup
from hlib import Harvest
B = "https://astree.univ-rouen.fr/_roman/reference/"
h = Harvest("deux-visages-de-l-astree")
parts = [("21_1", 1621, "I"), ("21_2", 1621, "II"), ("21_3", 1621, "III"), ("24_4", 1624, "IV")]
def clean(html):
    s = BeautifulSoup(html, "lxml")
    art = s.find("div", id="Page_content_goes_here") or s.find("article")
    for t in art.find_all(["script", "style", "nav", "audio", "img"]): t.decompose()
    for t in art.find_all("span", class_=["varp", "var_init", "cache", "italicspage"]): t.decompose()
    for t in art.find_all("a", class_="note"): t.decompose()
    for t in art.find_all("br"): t.replace_with("\n")
    paras = []
    for p in art.find_all("p"):
        tx = p.get_text().replace("\xa0", " ")
        tx = re.sub(r"[ \t]+", " ", tx)
        tx = re.sub(r" ?\n ?", "\n", tx).strip()
        if not tx or tx.startswith("Édition de 1607"): continue
        paras.append(tx)
    return "\n".join(paras)
for pid, yr, roman in parts:
    lim = h.get(B + f"{pid}/{pid}_liminaires.html", f"files/{pid}_liminaires.html")
    books = sorted(set(re.findall(rf'{pid}_livre_(\d+)\.html', lim)), key=int)
    texts = []
    for b in books:
        html = h.get(B + f"{pid}/{pid}_livre_{b}.html", f"files/{pid}_livre_{b}.html")
        texts.append(f"LIVRE {b}\n" + clean(html))
    raw = "\n\n".join(texts)
    print(pid, books, len(raw.split()))
    h.add(f"{pid}_reference.txt", raw, language="French", year=yr, source=f"Deux visages de L'Astrée, édition de référence, partie {roman}", url=B + f"{pid}/{pid}_liminaires.html")
print(h.finish(method="HTML crawl of the 'reference' version (1621 parts I-III, 1624 part IV; faithful text), livre_N pages only; removed variant spans of the 1607 edition (varp), note markers, page markers, glossary/character links kept as plain text; modernised 'fonctionnelle' and preliminary 1607/1610/1619 versions not fetched",
  coverage="All 12 (or so) books of each of the four parts of the reference edition. Liminaires pages (title pages, dedications, privileges, mixed with editorial commentary) and tables (contents) excluded.",
  problems=["Liminary period texts (dedications, privileges, poems) omitted because they are interleaved with editorial notes", "Text uses 1621 readings ('var21'/'var21nouveau'); 1607 readings dropped", "No robots.txt on server (404)"]))
