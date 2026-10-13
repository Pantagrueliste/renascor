import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, glob, os, tarfile, io
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
h = Harvest("kaiserin-eleonora-magdalena-korrespondenz")
tgz = "files/emt-working-data.tar.gz"
if not (h.dir / tgz).exists():
    h.get("https://codeload.github.com/emt-project/emt-working-data/tar.gz/main", tgz, binary=True)
nodate = 0
with tarfile.open(h.dir / tgz) as t:
    for m in sorted(t.getmembers(), key=lambda m: m.name):
        if not (m.isfile() and m.name.endswith(".xml") and "/data/" in m.name):
            continue
        xml = t.extractfile(m).read().decode("utf-8")
        y = None
        mm = re.search(r'<origDate\b[^>]*\bwhen-iso="([^"]+)"', xml)
        if mm: y = first_year(mm.group(1))
        if not y:
            ca = re.search(r'<correspAction type="sent".*?</correspAction>', xml, re.S)
            if ca:
                mm = re.search(r'<date\b[^>]*\b(?:when|when-iso|notBefore|notAfter)="([^"]+)"', ca.group(0))
                if mm: y = first_year(mm.group(1))
        if not y:
            mm = re.search(r'<date\b[^>]*\bwhen-iso="(\d{4})', xml[xml.find("<text"):])
            if mm: y = int(mm.group(1))
        if not y:
            nodate += 1
        tx = xml[xml.find("<text"):]
        tx = re.sub(r"<abbr\b[^>]*>.*?</abbr>", "", tx, flags=re.S)  # keep expansion only
        raw = '<TEI xmlns="http://www.tei-c.org/ns/1.0">' + tx
        lang = "German"
        h.add(os.path.basename(m.name), raw, language=lang, year=y, source="Familiensache? Korrespondenz der Kaiserin Eleonora Magdalena", url="https://github.com/emt-project/emt-working-data/blob/main/" + m.name.split("/",1)[1])
print(h.finish(method="Downloaded the GitHub tarball of emt-project/emt-working-data (main); one record per letter TEI file (1605); raw = <text> element with <abbr> removed where an <expan> is given. Year = origDate@when-iso, else correspAction[sent] date, else first date in body.",
  coverage="All 1,605 letters of the edition (letters after 1700 kept in staging with their year and counted out).",
  problems=[f"{nodate} letters without any usable date (year=None, dateless_in_window=False).", "Language set to German for all (header: 11 'und', 1 Latin; a few passages in other languages).", "Working data, not necessarily identical to published site versions."]))
