import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR)
from hlib import Harvest, tei_doc_year, slug
h = Harvest("cordican", delay=0.5)
B = "https://www.ull.es/corpora/cordican/"
# The stats action is broken on this instance (empty reply); list the corpus folder via action=files.
pg = h.get(B + "index.php?action=files&folder=xmlfiles/CORDICan", "files/files_CORDICan.html")
ids = sorted(set(re.findall(r"action=file&id=(CORDICan/[^'\"&>]+?\.xml)", pg)))
print(len(ids), "documents in xmlfiles/CORDICan")
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
          source="CORDICan — Corpus Documental de las Islas Canarias",
          url=B + "index.php?action=getxml&cid=" + cid)
probs.append(f"{undated} of {len(ids)} documents have no extractable date in the TEI header: year=None, "
             "dateless_in_window=False, so not counted in window (the corpus covers the 16th-19th centuries; "
             "some undated ones may be in window).")
probs.append("Only the xmlfiles/CORDICan folder was harvested; the instance also hosts other folders "
             "(Irene_Bello, Miguel_Inquisición, Pruebas_curso, Tesis_Cira) and root-level test files, which "
             "belong to other projects/tests. Raw TEI XML kept as harvested; year from origDate/msDesc.")
print(h.finish(method="Document ids from the files listing of folder xmlfiles/CORDICan (action=files&folder=...), "
                 "raw TEI via action=getxml&cid= (the stats action returns an empty reply on this instance); "
                 "year from the TEI header document date.",
               coverage=f"All {len(ids)} documents in xmlfiles/CORDICan (other folders on the instance excluded).",
               problems=probs))
