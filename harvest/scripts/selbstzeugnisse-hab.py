import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, io, re, zipfile
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
from lxml import etree
h = Harvest("selbstzeugnisse-hab")
T = "http://www.tei-c.org/ns/1.0"
XID = "{http://www.w3.org/XML/1998/namespace}id"
P = etree.XMLParser(recover=True, huge_tree=True)
probs = []
# 1. Diary of August the Younger: one record per dated entry
x = h.get("http://selbstzeugnisse.hab.de/edition/diarium/download", "files/diarium.xml")
root = etree.fromstring(x.encode("utf-8"), P)
n = noy = 0
for d in root.iter("{%s}div" % T):
    i = d.get(XID) or ""
    if not i.startswith("E1"):
        continue
    dt = d.find(".//{%s}date" % T)
    yr = first_year(dt.get("when")) if dt is not None and dt.get("when") else first_year(i)
    noy += yr is None
    for nt in list(d.iter("{%s}note" % T)):   # editorial annotations/translations
        pass
    raw = f'<TEI xmlns="{T}"><teiHeader/><text><body>' + etree.tostring(d, encoding="unicode") + "</body></text></TEI>"
    fn = f"august_{i}.xml"
    if fn in h.seen: fn = f"august_{i}_{n}.xml"
    h.add(fn, raw, language="German", year=yr, source="Diarium Herzog Augusts d. J. (Cod. Guelf. 42.19 Aug. 2°)", url="http://selbstzeugnisse.hab.de/edition/diarium/download")
    n += 1
print(n, "August entries")
# 2. Diaries of Ludwig Rudolph and Christine Luise: one record per manuscript file
zb = h.get("http://selbstzeugnisse.hab.de/downloads/sz2.zip", "files/sz2.zip", binary=True)
z = zipfile.ZipFile(io.BytesIO(zb))
FALL = {"cod_guelf_28_blank": 1701, "cod_guelf_286_blank": 1712, "cod_guelf_286a_blank": 1707, "cod_guelf_211_1_extrav": 1698}
for nme in sorted(z.namelist()):
    m = re.fullmatch(r"sz2/tagebuecher/(cod_guelf_[a-z0-9_]+)\.xml", nme)
    if not m: continue
    key = m.group(1)
    raw = z.read(nme).decode("utf-8")
    r = etree.fromstring(raw.encode("utf-8"), P)
    b = r.find(".//{%s}body" % T)
    yr = None
    for dt in (b.iter("{%s}date" % T) if b is not None else []):
        if dt.get("when") and first_year(dt.get("when")):
            yr = first_year(dt.get("when")); break
    if yr is None:
        base = re.sub(r"_teil\d$", "", key)
        yr = FALL.get(base)
        probs.append(f"{key}: no dated element, year set from manuscript ({yr})")
    h.add(key + ".xml", raw, language="German", year=yr, source="Tagebuch " + key.replace("_", " "), url="http://selbstzeugnisse.hab.de/downloads/sz2.zip")
probs += [f"{noy} August entries without year.",
  "August diary split per dated entry (E-divs, as the edition does); the 1594 title page/front list and year headings outside the entries not included. Diaries of Ludwig Rudolph/Christine Luise kept one record per manuscript (the edition does not divide them into entries).",
  "Ludwig Rudolph manuscripts (1701, 1707, 1712-13, 1724) are after 1700 and stay out of window; Christine Luise's 1698/99 diary is in window.",
  "Passages in Latin and other languages inside the diaries counted as German.",
  "Editorial translations/annotations sit in <note> elements, which the RQ counter drops. Grand Tour digital (separate entry) not harvested."]
print(h.finish(method="August diary: TEI download http://selbstzeugnisse.hab.de/edition/diarium/download (parsed with lxml recover because of duplicate xml:ids). Other diaries: http://selbstzeugnisse.hab.de/downloads/sz2.zip, sz2/tagebuecher/*.xml.",
  coverage="Complete diary of August the Younger 1594-1635 (all dated entries) and all seven TEI files of the sz2 diaries (Ludwig Rudolph 1701 incl. appendices, 1707, 1712-13; Christine Luise 1698-99).", problems=probs))
