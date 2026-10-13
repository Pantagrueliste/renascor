import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys; sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
import re, html
h = Harvest("nachlassinventar-ferdinand-ii-1596")
url = "https://repository.khm.at/viewer/api/v1/records/92663/plaintext"
raw = h.get(url, "files/plaintext.html")
s = re.sub(r"(?i)<br\s*/?>|</p>", "\n", raw)
s = re.sub(r"<[^>]+>", "", s)
s = html.unescape(s).replace("\xa0", " ")
lines = [re.sub(r"[ \t]+", " ", l).strip() for l in s.split("\n")]
out, folio = [], 0
for l in lines:
    if not l: continue
    if re.fullmatch(r"\d+\s?[rv]", l):
        folio += 1; continue
    out.append(l)
text = "\n".join(out)
h.add("Nachlassinventar_Ferdinand_II_1596.txt", text, language="German", year=1596,
      source="Das Nachlassinventar Erzherzog Ferdinands II. von 1596 (KHM KK_6652)", url=url)
print(h.finish(method="Repository plain-text API (record 92663) returns the whole transcription as HTML fragments; tags stripped, entities decoded, standalone folio labels (e.g. '1r') removed.",
 coverage="all (single inventory manuscript)", problems=[f"{folio} standalone folio labels removed; original-spelling German with Latin/Italian item names mixed in"]))
