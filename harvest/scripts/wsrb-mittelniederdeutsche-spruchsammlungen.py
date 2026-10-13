import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, tei_year
h = Harvest("wsrb-mittelniederdeutsche-spruchsammlungen")
B = "https://digibib.uni-rostock.de/wsrb/xml_raw/"
for k in ["wsrb_tr1-ws1","wsrb_tr2-ws2","wsrb_tr3-ws3","wsrb_tr4-ws4","wsrb_tr5-ws5","wsrb_tr6-ws6","wsrb_tr7-ws7","wsrb_tr8-rbl"]:
    raw = h.get(f"{B}{k}.tei.xml", f"files/{k}.tei.xml")
    y = tei_year(raw)
    print(k, y)
    t = re.search(r"<title>([^<]+)</title>", raw).group(1)
    h.add(k + ".tei.xml", raw, language="Middle Low German", year=y, source="WSRB: " + t, url=f"{B}{k}.tei.xml")
rep = h.finish(method="Fetched the eight transcription TEI files from /wsrb/xml_raw/<id>.tei.xml (links on the Daten/TEI page).",
  coverage="All 8 transcriptions (7 Werltspröke editions + Rimbökelin). The critical edition TEI (wsrb_edition) was not harvested, to avoid duplicating the sayings.",
  problems=["Year from sourceDesc dates of each print (check)."])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"])
