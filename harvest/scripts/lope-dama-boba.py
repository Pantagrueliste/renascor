import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, tei_year, first_year

h = Harvest("lope-dama-boba")
U = "https://damaboba.unibo.it/xml/edicion_critica.xml"
raw = h.get(U, "files/edicion_critica.xml")
t = raw[raw.find("<text"):raw.find("</text>") + 7]
t = re.sub(r"<app\b.*?</app>", "", t, flags=re.S)       # variant apparatus
t = re.sub(r"<note\b.*?</note>", "", t, flags=re.S)     # commentary notes
t = re.sub(r"<ptr\b[^>]*/>", "", t)
h.add("edicion_critica.xml", "<TEI>" + t + "</TEI>", language="Spanish", year=1613,
      source="Lope de Vega, La dama boba (critical edition)", url=U)
rep = h.finish(method="Downloaded edicion_critica.xml; kept <text>, removed <app> apparatus and <note> commentary.",
  coverage="All of the critical text (1 play).",
  problems=["Year 1613 = date of the autograph (printed 1617); critical text, not a diplomatic transcription of one witness."])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"])
