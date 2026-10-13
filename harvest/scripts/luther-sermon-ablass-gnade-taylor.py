import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, tei_year, first_year

h = Harvest("luther-sermon-ablass-gnade-taylor")
U = "https://editions.mml.ox.ac.uk/texts/ablassgnade6.xml"
raw = h.get(U, "files/ablassgnade6.xml")
t = raw[raw.find("<text"):raw.find("</text>") + 7]
t = re.sub(r"<note\b.*?</note>", "", t, flags=re.S)     # English footnotes
h.add("ablassgnade6.xml", "<TEI>" + t + "</TEI>", language="German", year=1518,
      source="Luther, Ein Sermon von Ablass und Gnade (Leipzig 1518), Taylor Editions", url=U)
rep = h.finish(method="Downloaded the TEI file; kept <text>, removed editorial footnotes.",
  coverage="All (1 text).", problems=["Year 1518 from the print; TEI file dates (2018) are of the edition."])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"])
