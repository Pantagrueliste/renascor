import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys; sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
from lxml import etree
import re, zipfile, io
h = Harvest("dio")
base = "https://epigraf.inschriften.net/files/download/"
dumps = {"di7_epidoc": "77651", "di77_epidoc": "77647", "di102_epidoc": "77661"}
T = "{http://www.tei-c.org/ns/1.0}"
LANGS = [("lateinisch", "Latin"), ("niederdeutsch", "Low German"), ("hochdeutsch", "German"), ("deutsch", "German"),
         ("hebr", "Hebrew"), ("griechisch", "Greek")]
def lang_of(s):
    s = s.lower(); best = None
    for k, v in LANGS:
        i = s.find(k)
        if i >= 0 and (best is None or i < best[0]): best = (i, v)
    return best[1] if best else "Latin"
MOD = {"A": 10, "M": 50, "E": 90, "1.D": 15, "2.D": 50, "3.D": 85, "1.H": 25, "2.H": 75, "1.V": 12, "2.V": 37, "3.V": 62, "4.V": 87}
approx = 0
def year_of(s):
    global approx
    m4 = re.search(r"(?<!\d)(\d{3,4})(?!\d)", s)
    if m4: return int(m4.group(1))
    m = re.search(r"(?:(A|M|E|[1-4]\.[DHV])\.)?\s*(\d{1,2})\.", s)
    if not m: return None
    approx += 1
    return (int(m.group(2)) - 1) * 100 + MOD.get(m.group(1), 50)
probs = []
for name, fid in dumps.items():
    z = h.get(base + fid, f"files/{name}.zip", binary=True)
    zf = zipfile.ZipFile(io.BytesIO(z))
    for n in sorted(zf.namelist()):
        if not n.endswith(".xml"): continue
        raw = zf.read(n).decode("utf-8")
        root = etree.fromstring(raw.encode("utf-8"))
        ed = root.xpath("//t:text/t:body/t:div[@type='edition']", namespaces={"t": T[1:-1]})
        if not ed:
            probs.append(f"{n}: no edition div"); continue
        div = ed[0]
        for hd in list(div.iter(T + "head")):
            hd.getparent().remove(hd)
        od = root.xpath("//t:origDate", namespaces={"t": T[1:-1]})
        y = year_of(" ".join(od[0].itertext())) if od else None
        if y is None: probs.append(f"{n}: no date")
        lg = root.xpath("//t:langUsage/t:language", namespaces={"t": T[1:-1]})
        lang = lang_of("".join(lg[0].itertext())) if lg else "Latin"
        title = " ".join("".join(root.xpath("//t:titleStmt/t:title", namespaces={"t": T[1:-1]})[0].itertext()).split())
        h.add(f"{name.split('_')[0]}_{n}", "<text><body>" + etree.tostring(div, encoding="unicode") + "</body></text>",
              language=lang, year=y, source=f"Deutsche Inschriften Online ({name.split('_')[0].upper()}): {title}",
              url="https://epigraf.inschriften.net/pages/dumps", title=title)
probs.append(f"{approx} dates were century/part-century expressions (e.g. '15.Jh.', 'M.16.Jh.') converted to a mid-point year")
probs.append("Only 3 volumes (DI 7 Braunschweig, DI 77 Greifswald, DI 102 Stralsund; 978 articles) have inscription transcriptions as EpiDoc; the full CGIF dump (31,197 articles) holds only titles/dates/keywords, no texts, so the other ~25,900 in-period articles cannot be harvested")
print(h.finish(method="Epigraf dumps page: downloaded the three EpiDoc zips (di7, di77, di102); one record per article, keeping only <div type=edition> (the inscription transcription), dropping modern translation, commentary and bibliography. CGIF dump downloaded and inspected (metadata only, not ingested).",
 coverage="Partial: 978 of 31,197 articles (3 volumes with EpiDoc transcriptions); remaining volumes only exist as printed/portal text (portal behind bot check) or announced future dumps", problems=probs))
