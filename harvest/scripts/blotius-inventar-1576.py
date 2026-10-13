import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, tei_year, first_year

h = Harvest("blotius-inventar-1576")
U = "https://edition.onb.ac.at/o:blo.inventar-mz/TEI_SOURCE"
raw = h.get(U, "files/blo.inventar-mz.xml")
t = raw[raw.find("<text"):raw.find("</text>") + 7]
t = re.sub(r"<reg\b.*?</reg>", "", t, flags=re.S)       # keep original spelling (orig), drop regularised
t = re.sub(r"<expan\b.*?</expan>", "", t, flags=re.S)   # keep abbreviations as written
t = re.sub(r"<note\b.*?</note>", "", t, flags=re.S)     # keep? notes are contemporary glosses on format; see below
h.add("blo.inventar-mz.xml", "<TEI>" + t + "</TEI>", language="Latin", year=1576,
      source="Blotius, Inventarii bibliothecae S.C. Maiestatis pars posterior (ÖNB Cod. 13525)", url=U)
rep = h.finish(method="Downloaded the TEI_SOURCE file; kept <text> with original-spelling readings (removed <reg>/<expan>).",
  coverage="The whole transcribed volume (letters M-Z as far as transcribed; the site says N-U are not transcribed).",
  problems=["<note> elements (e.g. 'in libro compactae') removed as annotation; they may be partly period text, so word count is slightly low.",
            "Single record for the whole inventory (656 entries)."])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"])
