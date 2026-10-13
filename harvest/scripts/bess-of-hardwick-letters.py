import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, io, zipfile
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
h = Harvest("bess-of-hardwick-letters")
U = "https://www.dhi.ac.uk/san/data/bessofhardwick/bessofhardwick.zip"
data = h.get(U, "files/bessofhardwick.zip", binary=True)
z = zipfile.ZipFile(io.BytesIO(data))
sql = [n for n in z.namelist() if n.endswith(".sql")][0]
sqltxt = z.read(sql).decode("utf-8", "replace")
years = {}
for m in re.finditer(r"\((\d+),'((?:[^'\\]|\\.)*)',(\d{8}),(?:'(?:In|Out)|NULL)", sqltxt):
    years[int(m.group(1))] = int(m.group(3)[:4])
print(len(years), "dates from SQL")
undated = 0
for n in sorted(z.namelist()):
    if not (n.startswith("bess_letters_xml/") and n.endswith(".xml")): continue
    raw = z.read(n).decode("utf-8")
    lid = int(re.search(r'<bess_letter id="(\d+)"', raw).group(1))
    # keep only the letter itself (address leaf + text): drop copyright, change history and archivist notes
    m = re.search(r"<bess_letter\b.*?</bess_letter>", raw, re.S)
    body = re.sub(r'<note hand="archivist"[^>]*>.*?</note>', "", m.group(0), flags=re.S)
    y = years.get(lid)
    if y is None:
        undated += 1
    h.add(f"{lid:03d}.xml", f"<TEI><text><body>{body}</body></text></TEI>", language="English", year=y,
          source=f"Bess of Hardwick's Letters, letter {lid}", url="https://www.bessofhardwick.org/letter.jsp?letter=%d" % lid)
rep = h.finish(method="Downloaded the DHI data-service zip (XML letters + SQL metadata); year from letters.sort_date in the SQL dump.",
  coverage="All 234 letters, diplomatic transcription (the XML is the single diplomatic version, with abbreviation expansions as inline tags). Normalised transcripts are not in the download.",
  problems=["Some dates are conjectural (e.g. '[1600?]'); year taken from sort_date.", "%d letters without date." % undated,
            "Not TEI: wrapped in <TEI><text><body> so RQ's counter works; copyright block, change history and archivist notes removed."])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"])
