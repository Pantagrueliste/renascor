import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, json
HD = HARVEST_DIR + ""
sys.path.insert(0, HD)
from hlib import Harvest
import posixpath, urllib.parse
h = Harvest("maurolico-opera-mathematica")
B = "https://people.dm.unipi.it/maurolic/"
pianta = h.get(B + "pianta.htm", "files/pianta.htm")
intros = sorted(set(re.findall(r'(?i)href="(edizioni/[^"#]+)"', pianta)))
res = {}
for i in intros:
    s = h.get(B + i, "files/" + i)
    d = posixpath.dirname(i)
    links = sorted(set(re.findall(r'(?i)href="([^"#]+\.htm)"', s)))
    res[i] = [posixpath.normpath(posixpath.join(d, l)) for l in links if not l.startswith(("http", "../../../"))]
json.dump(res, open(HD + "/tmp/mauro_links.json", "w"), indent=1)
for k, v in res.items(): print(k, len(v), v[:4])
