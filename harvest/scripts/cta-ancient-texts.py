import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR)
from hlib import Harvest, tei_doc_year, slug
h = Harvest("cta-ancient-texts")
B = "http://teitok.clul.ul.pt/cta/"
ids = []
start = 0
while True:
    pg = h.get(B + f"index.php?action=stats&start={start}", f"files/stats_{start}.html")
    batch = re.findall(r"cid=([^'\"&>]+?\.xml)", pg)
    if not batch:
        break
    ids += batch
    start += 30
ids = sorted(set(i for i in ids if not i.startswith("Test/")))  # Test/ holds platform test files
print(len(ids), "documents in stats (Test/ excluded)")
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
    h.add(fn + ".xml", x, language="Portuguese", year=yr,
          source="CTA — Corpus de Textos Antigos", url=B + "index.php?action=getxml&cid=" + cid)
probs.append(f"{undated} of {len(ids)} documents have no extractable date in the TEI header: year=None, "
             "dateless_in_window=False, so not counted in window.")
probs.append("Raw TEI XML kept as harvested (RQ's counter keeps only <text>/<body>); year from origDate/msDesc "
             "(document date), not the composition date in sourceDesc.")
print(h.finish(method="Document ids from the stats pages (action=stats&start=...), raw TEI via action=getxml&cid=; "
                 "Test/ folder excluded; year from the TEI header document date.",
               coverage=f"All {len(ids)} corpus documents listed on the statistics pages (Test/ platform files excluded).",
               problems=probs))
