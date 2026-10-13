import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
from bs4 import BeautifulSoup
h = Harvest("book-of-margery-kempe-selu", delay=1.0)
U = "https://english.selu.edu/kempe/showcase/webapp_wynkyn.php"
s = h.get(U, "files/webapp_wynkyn.php.html")
soup = BeautifulSoup(s, "lxml")
right = soup.find(id="content-right")
lines = []
for f in right.select("div.folio"):
    fid = f.get("id")
    for d in f.find_all("div", class_=re.compile(r"^(ab|ab-short)$")):
        if d.find_parent("div", class_=re.compile(r"^(ab|ab-short)$")): continue
        for e in d.select(".expan, .add-top-right, .add-bottom-right, .add-bottom-LIBRARIAN"): e.decompose()
        t = re.sub(r"\s+", " ", d.get_text(" ", strip=False)).strip()
        t = re.sub(r"\s+([.,;:/])", r"\1", t)
        if t: lines.append(t)
txt = "\n".join(lines)
h.add("wynkyn-de-worde-treatise.txt", txt, language="Middle English", year=1501,
      source="Here begynneth a shorte treatyse of contemplacyon (Wynkyn de Worde, c. 1501), diplomatic transcription, Cambridge UL Sel.5.27", url=U)
rep = h.finish(method="Showcase viewer page for the Wynkyn de Worde pamphlet (webapp_wynkyn.php) fetched once; folio divs parsed, diplomatic abbreviated forms kept (<span class=abbr>), expansions (<span class=expan>) and added marginal folio numbers dropped.",
  coverage="The Wynkyn de Worde pamphlet only (the one in-period text). The manuscript Book of Margery Kempe (BL Add. 61823, c. 1440) is out of window and was not harvested.",
  problems=["Abbreviation marks are Unicode combining characters from the site's Andron/MUFI encoding; word counts depend on spacing of line-end splits (words broken across lines are kept as split).",
            "Year 1501 is the printed date 'c. 1501'."])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"])
