import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, json
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
h = Harvest("leibniz-reihe-viii")
tree = json.load(open(HARVEST_DIR + "/work/t/ltree.json"))
paths = [x["path"] for x in tree["tree"] if x["type"] == "blob" and "/tei/Einzeldateien/" in x["path"] and re.search(r"/L_(chapter|section)_\d+\.xml$", x["path"])]
print(len(paths), flush=True)
for p in paths:
    h.get("https://raw.githubusercontent.com/telota/LeibnizVIII-LaTeX_TEI/main/" + p.replace(" ", "%20"), "files/" + p)
print("done")
