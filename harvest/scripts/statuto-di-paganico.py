import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, html
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
U = "http://web.archive.org/web/20050217022521id_/http://www.gol.grosseto.it/puam/arcstato/paganico/pagedi.htm"
h = Harvest("statuto-di-paganico", delay=2.0)
raw = h.get(U, "files/pagedi.htm")
x = re.sub(r"<!--.*?-->", "", raw, flags=re.S)           # index tags
x = re.sub(r"<(script|style)\b.*?</\1>", "", x, flags=re.S | re.I)
x = re.sub(r"<(?:br|/p|/h[1-6]|/center|/tr)[^>]*>", "\n", x, flags=re.I)
t = html.unescape(re.sub(r"<[^>]+>", "", x)).replace("\xa0", " ")
a = t.find("Prima distinctione")
b = t.find("Rubriche de la prima distinctione")
body = t[a:b]
body = re.sub(r"C\.\s*(?:[IVXL]+|\d+)\s*[rv]\.?", " ", body)           # folio markers
body = re.sub(r"<\s*[IVX]+\s*,\s*\d+\s*>", " ", body)                    # rubric numbers
body = re.sub(r"\((?:[a-z]{1,2})\)", "", body)                           # footnote call letters
body = re.sub(r"[ \t]+", " ", body)
body = "\n".join(l.strip() for l in body.split("\n") if l.strip())
print(len(body.split()))
h.add("paganico_statuto.txt", body, language="Italian", year=1487, source="Lo statuto di Paganico (edizione), Archivio di Stato di Grosseto", url=U)
print(h.finish(method="Internet Archive capture (2004/2005) of the 'Edizione' page pagedi.htm, fetched raw (id_ flavour) over http; kept the statute text from the first distinctio to the end of the fifth, removed HTML, index tags, folio markers (C.XIr.), rubric numbers (<I,21>) and footnote call letters; the codex's own table of rubrics at the end of the page (Rubriche de la prima distinctione ...) excluded as an index",
  coverage="Full statute text (five distinctiones, rubrics included as in the edition). Introduction, chapters I-II, hand table and index of rubrics pages not fetched.",
  problems=["Original site is gone; text taken from the Wayback Machine (capture of 2004-10-30 served for the 2005-02-17 request)", "Year 1487 is the first Sienese approval date given in the catalogue (approvals 1487, 1489, 1490); the text itself contains earlier inserted material (e.g. 1440-41 Sienese decrees)", "The edition's footnote apparatus is not in the page, only call letters, which were removed", "web.archive.org over https refused connections from this host; plain http worked"]))
