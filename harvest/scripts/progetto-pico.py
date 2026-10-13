import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, html
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
h = Harvest("progetto-pico")
U = "https://web.archive.org/web/20250913124312id_/https://www.brown.edu/Departments/Italian_Studies/pico/oratio.html"
t = h.get(U, "files/oratio.html")
body = t[t.lower().find("<body"):]
body = re.sub(r"<p>", "\n", body, flags=re.I)
body = html.unescape(re.sub(r"<[^>]+>", "", body))
lines = [l.strip() for l in body.split("\n")]
lines = [l for l in lines if l and l != "Oratio de hominis dignitate"]
txt = "\n".join(lines)
h.add("oratio.txt", txt, language="Latin", year=1496, source="Progetto Pico: Oratio de hominis dignitate (Bologna 1496 edition)", url="https://www.brown.edu/Departments/Italian_Studies/pico/oratio.html")
print(h.finish(method="Read the Wayback copy (13 Sept 2025, raw id_) of oratio.html; Latin transcription of the editio princeps (paras 1-47); tags and section numbers symbols removed.",
 coverage="The one work (Oratio) harvested in full; commentary, annotated text, introductions and the Apologia (images only) not included.",
 problems=["Original brown.edu address returns 404; read from the Internet Archive copy.", "Year 1496 = date of the printed edition transcribed (composed 1486)."]))
