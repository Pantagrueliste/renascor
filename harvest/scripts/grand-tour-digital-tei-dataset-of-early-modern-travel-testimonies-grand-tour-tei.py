import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, glob, zipfile
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
h = Harvest("grand-tour-digital-tei-dataset-of-early-modern-travel-testimonies-grand-tour-tei")
h.get("https://zenodo.org/api/records/23055358/files/grand-tour-tei.zip/content", "files/grand-tour-tei.zip", binary=True)
z = zipfile.ZipFile(h.dir / "files/grand-tour-tei.zip")
for n in sorted(z.namelist()):
    if "/Reiseberichte/cod_" in n and n.endswith(".xml"):
        x = z.read(n).decode("utf-8")
        ds = re.findall(r'<date\b[^>]*\bwhen="(\d{4})', x)
        y = int(ds[0]) if ds else None
        h.add(n.split("/")[-1], x, language="German", year=y, source="Grand Tour digital (HAB Wolfenbüttel)", url="https://zenodo.org/records/23055358")
print(h.finish(method="Zenodo record 23055358 zip (TEI-XML repository); only transcribed travel journals under Reiseberichte/ taken, introductions, registers and index excluded; year = first <date when> in the body",
  coverage="All 4 travel-journal TEI files in the deposit (the deposit holds no other primary texts; introduction/ files are modern editorial text). Corpus is 1652-1701.",
  problems=["Cod. Guelf. 149.14 Extrav. is dated 1701-1702, outside window", "Texts are Transkribus HTR with manual correction; TEI header says TEI conversion with LLM help", "Year is that of first dated entry, not a header field"]))
