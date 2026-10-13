import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
h = Harvest("bodleian-first-folio")
B = "https://firstfolio.bodleian.ox.ac.uk"
page = h.get(B + "/downloads.html", "files/downloads.html")
codes = list(dict.fromkeys(re.findall(r'/download/xml/(F-[^"/]+)\.xml', page)))
print(len(codes))
for c in codes:
    raw = h.get(f"{B}/download/xml/{c}.xml", f"files/{c}.xml")
    t = re.search(r"<title[^>]*>([^<]+)</title>", raw)
    h.add(c + ".xml", raw, language="English", year=1623, source="Bodleian First Folio: " + (t.group(1).strip() if t else c),
          url=f"{B}/download/xml/{c}.xml")
rep = h.finish(method="Downloaded the per-play TEI XML files linked from the downloads page.",
  coverage="All 36 plays of the First Folio transcription.",
  problems=["Year set to 1623 (date of the printed volume), not composition date.", "Footnotes/editorial notes in XML are not stripped; RQ counter keeps only <text>/<body>."])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"])
