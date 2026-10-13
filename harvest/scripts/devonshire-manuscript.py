import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, tarfile, os
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
h = Harvest("devonshire-manuscript")
tgz = "files/devonshire-ms.tar.gz"
if not (h.dir / tgz).exists():
    h.get("https://codeload.github.com/etcluvic/devonshire-ms/tar.gz/main", tgz, binary=True)
def strip_notes(t, types):
    for _ in range(5):
        t2 = re.sub(r'<note\b[^>]*\btype="(?:%s)"[^>]*?(?:/>|>(?:(?!<note\b).)*?</note>)' % types, "", t, flags=re.S)
        if t2 == t: break
        t = t2
    return t
n = 0
with tarfile.open(h.dir / tgz) as t:
    for m in sorted(t.getmembers(), key=lambda m: m.name):
        if not (m.isfile() and "Devonshire Manuscript poems/" in m.name and m.name.endswith(".xml")): continue
        fn = os.path.basename(m.name)
        if "frontmatter" in fn: continue
        xml = t.extractfile(m).read().decode("utf-8")
        tx = xml[xml.find("<text"):]
        tx = re.sub(r"<head\b.*?</head>", "", tx, flags=re.S)
        tx = strip_notes(tx, "intro|context|editorial")
        tx = re.sub(r"<abbr\b[^>]*>.*?</abbr>", "", tx, flags=re.S)
        raw = '<TEI xmlns="http://www.tei-c.org/ns/1.0">' + tx
        h.add(fn, raw, language="English", year=1540, source="Social Edition of the Devonshire MS (BL Add MS 17492)", url="https://github.com/etcluvic/devonshire-ms")
        n += 1
print(h.finish(method="Downloaded the GitHub tarball of etcluvic/devonshire-ms (main); one record per file in 'Devonshire Manuscript poems' (the diplomatic machine-readable transcription of the manuscript, one poem/item per file); raw = <text> with headnotes (<head>), intro/context/editorial notes and <abbr> (expansion kept) removed.",
  coverage="All poem/item files of the manuscript transcription (frontmatter file LDev000 excluded). The 288 'witnesses' files (copies of the same poems in other manuscripts and prints, e.g. STC prints, Egerton MS) were not harvested: they are other sources, with their own dates, and belong to other collections.",
  problems=["No per-item date: year set to 1540 for all (manuscript compiled c. 1532-1547; catalogue c. 1539-1547).", "Some editorial matter within <note type=annotation> may remain (marginalia are period text)."]))
