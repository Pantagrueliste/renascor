import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR)
from hlib import Harvest, tei_doc_year, slug
h = Harvest("cordina-north-america")
B = "https://corpora.uah.es/cordina/"
ids = []
start = 0
while True:
    pg = h.get(B + f"index.php?action=stats&start={start}", f"files/stats_{start}.html")
    batch = re.findall(r"cid=([^'\"&>]+?\.xml)", pg)
    if not batch:
        break
    ids += batch
    start += 30
ids = sorted(set(ids))
print(len(ids), "documents in stats")
probs = []
undated = 0
for cid in ids:
    fn = slug(cid)
    try:
        x = h.get(B + "index.php?action=getxml&cid=" + cid, f"files/{fn}.xml")
    except Exception as e:
        probs.append(f"{cid}: {e}")
        continue
    yr = tei_doc_year(x)
    undated += yr is None
    h.add(fn + ".xml", x, language="Spanish", year=yr,
          source="CORDINA — Corpus diacrónico del español de Norteamérica",
          url=B + "index.php?action=getxml&cid=" + cid)
probs.append(f"{undated} of {len(ids)} documents have no extractable date in the TEI header: year=None, "
             "dateless_in_window=False, so not counted in window (the corpus covers the 16th-20th centuries; "
             "some undated ones may be in window).")
probs.append("Raw TEI XML kept as harvested (RQ's counter keeps only <text>/<body>); year from origDate/msDesc "
             "(document date). Texts also appear in the CHARTA corpus (same CHARTA network files).")
print(h.finish(method="Document ids from the stats pages (action=stats&start=...), raw TEI via action=getxml&cid=; "
                 "year from the TEI header document date.",
               coverage=f"All {len(ids)} documents listed on the statistics pages.",
               problems=probs))
