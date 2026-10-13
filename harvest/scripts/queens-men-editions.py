import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
h = Harvest("queens-men-editions")
base = "https://lemdo.uvic.ca/qme/xml/source/"
files = {"emdFV_Q1": "The Famous Victories of Henry the Fifth", "emdFBFB_Q1": "Friar Bacon and Friar Bungay",
         "emdLeir_Q1": "King Leir", "emdSel_Q": "Selimus", "emdTTR3_Q1": "The True Tragedy of Richard III"}
probs = ["The Old Wives' Tale (emdOWT) has no TEI source online (edition page not available at harvest); not harvested.",
         "Modern-spelling versions (emd*_M.xml) not harvested (old-spelling quarto kept)."]
for f, title in files.items():
    raw = h.get(base + f + ".xml", f"files/{f}.xml")
    m = re.search(r"<docDate[^>]*>(.*?)</docDate>", raw, re.S)
    yr = first_year(m.group(1)) if m else None
    if yr is None:
        m = re.search(r"</docImprint>", raw)
        di = re.search(r"<docImprint.*?</docImprint>", raw, re.S)
        yr = first_year(re.sub(r"<[^>]+>", " ", di.group(0))) if di else None
    if yr is None:
        q = re.search(r"Quarto 1, (\d{4})", raw)
        yr = int(q.group(1)) if q else None
    if yr is None:
        probs.append(f"{f}: no docDate")
    # rejoin words split by end-of-line hyphens
    raw2 = re.sub(r'<pc force="weak">.*?</pc>\s*<lb[^>]*/>\s*', "", raw, flags=re.S)
    h.add(f + ".xml", raw2, language="English", year=yr, source="Queen's Men Editions: " + title, url=base + f + ".xml")
print(h.finish(method="Old-spelling TEI source files of the early quartos from lemdo.uvic.ca/qme/xml/source/; year from titlePage docDate; end-of-line hyphenation pc/lb removed so split words count once.",
 coverage="All 5 available plays (Famous Victories, Friar Bacon, King Leir, Selimus, True Tragedy of Richard III) in old spelling.", problems=probs))
