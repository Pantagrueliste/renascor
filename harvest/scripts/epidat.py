import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, csv
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
csv.field_size_limit(10**9)
h = Harvest("epidat")
t = h.get("https://gitlab.rlp.net/epidat/data/-/raw/main/tsv/id-year-transcription-translation.tsv", "files/id-year-transcription-translation.tsv")
rows = list(csv.reader(t.lstrip("﻿").splitlines(), delimiter="\t", quoting=csv.QUOTE_NONE))
odd = nodate = 0
for r in rows[1:]:
    if len(r) < 3 or not r[0].strip():
        continue
    if len(r) != 4: odd += 1
    rid, ys = r[0].strip(), r[1].strip()
    tr = r[2].replace("‎", "").replace("‏", "").strip()
    if not tr: continue
    m = re.search(r"(?<!\d)(\d{4})(?!\d)", ys)
    y = int(m.group(1)) if m else None
    if y is None: nodate += 1
    heb = len(re.findall(r"[֐-׿]", tr)); lat = len(re.findall(r"[A-Za-zäöüÄÖÜß]", tr))
    lang = "Hebrew" if heb >= lat else "German"
    h.add(rid + ".txt", tr, language=lang, year=y, source="epidat", url="https://www.steinheim-institut.de/cgi-bin/epidat?id=" + rid)
print(h.finish(method="Downloaded tsv/id-year-transcription-translation.tsv from the public GitLab repo epidat/data (main); one record per inscription (id), raw = transcription column only (the German translation column is excluded). Year = year column.",
  coverage="All inscriptions with a transcription in the TSV (the repository's bulk export of 322 editions); the per-monument TEI XML was not fetched because the TSV carries the same transcription and the catalogue counts on it. Out-of-window rows kept in staging.",
  problems=[f"{odd} rows had a stray tab (more than 4 columns): transcription taken from column 3 only.", f"{nodate} rows without a parseable year (year=None, dateless_in_window=False).", "Transcription is Hebrew, often followed by a German-language rendering of the stone's own text; language set to Hebrew when Hebrew letters dominate, else German."]))
