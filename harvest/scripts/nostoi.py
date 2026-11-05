import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR)
from hlib import Harvest, tei_doc_year, slug
h = Harvest("nostoi")
B = "https://corpora.uah.es/nostoi/"
pg = h.get(B + "index.php?action=files", "files/files.html")
ids = sorted(set(re.findall(r"action=file&id=([^'\"&>]+?\.xml)", pg)))
ids = [i for i in ids if not i.startswith("prueba")]  # prueba* are platform test files
print(len(ids), "documents in files listing:", ids)
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
          source="NOSTOI — Corpus de textos troyanos ibéricos", url=B + "index.php?action=getxml&cid=" + cid)
probs.append(f"{undated} of {len(ids)} documents have no extractable date in the TEI header: year=None, "
             "dateless_in_window=False, so not counted in window.")
probs.append("The TEITOK instance currently holds only 2 corpus documents (NOSTOI-01_HT, NOSTOI-02_CTc); the "
             "stats page lists just a test file. The remaining testimonies (NOSTOI-03 to NOSTOI-11) are presented "
             "on the static project site but are not yet in the TEITOK corpus.")
print(h.finish(method="Document ids from the files page (action=files), raw TEI via action=getxml&cid=; "
                 "prueba* test files excluded; year from the TEI header document date.",
               coverage=f"All {len(ids)} documents in the TEITOK files listing (the corpus is still being built).",
               problems=probs))
