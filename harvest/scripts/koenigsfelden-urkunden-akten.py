import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, io, zipfile, re
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, tei_year, first_year
from lxml import etree
h = Harvest("koenigsfelden-urkunden-akten")
url = "https://zenodo.org/api/records/10950031/files/Staatsarchiv-Aargau/koenigsfelden-data-v2024-04-09.zip/content"
z = zipfile.ZipFile(io.BytesIO(h.get(url, "files/koenigsfelden-data-v2024-04-09.zip", binary=True)))
NS = "{http://www.tei-c.org/ns/1.0}"
LANG = {"Frühneuhochdeutsch": "German", "Latein": "Latin", "Deutsch": "German", "Mittelhochdeutsch": "German"}
nolang = noyear = 0
for n in sorted(z.namelist()):
    if "/data/docs/" not in n or not n.endswith(".xml"):
        continue
    xml = z.read(n)
    root = etree.fromstring(xml)
    # year
    yr = None
    od = root.xpath("//t:sourceDesc//t:origDate", namespaces={"t": NS[1:-1]})
    for d in od:
        for a in ("when", "notBefore", "from", "notAfter", "to"):
            if d.get(a) and first_year(d.get(a)):
                yr = first_year(d.get(a)); break
        if yr is None and first_year("".join(d.itertext())):
            yr = first_year("".join(d.itertext()))
        if yr: break
    tl = root.xpath("//t:textLang", namespaces={"t": NS[1:-1]})
    lg = LANG.get("".join(tl[0].itertext()).strip()) if tl else None
    # strip editorial layers: abbreviations (keep expansions), editorial regularised punctuation, comments, corrections, facsimile
    for tag in ("abbr", "reg", "comment", "corr", "facsimile"):
        for el in list(root.iter(NS + tag)):
            p = el.getparent()
            if p is None: continue
            tail = el.tail
            prev = el.getprevious()
            if tail:
                if prev is not None: prev.tail = (prev.tail or "") + tail
                else: p.text = (p.text or "") + tail
            p.remove(el)
    raw = etree.tostring(root, encoding="unicode")
    if lg is None: nolang += 1
    if yr is None: noyear += 1
    h.add(n.split("/")[-1], raw, language=lg or "German", year=yr, source="Königsfelden Urkunden und Akten",
          url="https://doi.org/10.5281/zenodo.10950031")
print(h.finish(
  method="Zenodo 10950031 data dump (v2024-04-09); every TEI file in data/docs. Year = first origDate in sourceDesc; language from msItem/textLang (Frühneuhochdeutsch->German, Latein->Latin). Removed <abbr> (kept <expan>), editorial <reg> punctuation/stars, <comment>, <corr> (kept <sic>), facsimile.",
  coverage="All 1,557 document files (1291-1662); out-of-window ones stay in staging with their year. Registers (people, places, organisations, keywords) not included.",
  problems=[f"{nolang} files without textLang: defaulted to German (Latin possible).", f"{noyear} files without a usable origDate: year=None, not counted.",
            "Copybook entries (AA_*, 455 files) whose original also exists (U-17_*) are not transcribed (they only link to the original); other copybook entries may duplicate texts of originals."]))
