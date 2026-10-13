import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import re
import sys
HD = HARVEST_DIR + ""
sys.path[:0] = [HD, HD + "/scripts"]
from hlib import Harvest, first_year  # noqa: E402
import hab  # noqa: E402

RID = "magdeburger-zenturien-methode-hab"
ED = "ed000086"
problems = []
h = Harvest(RID)
files = [p for p in hab.mets_files(h, ED) if "/" in p and not p.startswith(("register/", "tei-"))]
n_fn = 0
for p in files:
    data = hab.fetch(h, ED, p, problems)
    if data is None:
        continue
    root = hab.parse(data)
    year = None
    for d in root.iter("{*}origDate"):
        year = first_year(d.get("when") or d.get("notBefore") or d.get("from") or "".join(d.itertext()))
        if year:
            break
    if year is None:
        m = re.match(r"(\d\d)\d{4}", p.split("/")[-1])
        if m:
            year = 1500 + int(m.group(1))
            n_fn += 1
    hab.normalise(root)
    body = hab.body_el(root)
    lang = hab.dominant_lang(root, None)
    if lang is None:
        lang = hab.guess_lang(hab.plain(body) if body is not None else "", "Latin")
    h.add(p.split("/")[-1], hab.serialise(root), language=lang, year=year,
          source="Magdeburger Zenturien: Historische Methode und Arbeitstechnik, HAB Wolfenbüttel", url=hab.HAB + ED + "/" + p)
if n_fn:
    problems.append(f"{n_fn} files without origDate: year taken from the YYMMDD file-name prefix (15YY)")
problems.append("language by xml:lang where marked, else by a stop-word count (Latin/German)")
print(h.finish(
    method="Document files (Ort/Archiv/YYMMDD_*.xml) listed in mets.xml, fetched one by one; sic kept / corr dropped, apparatus variants dropped, footnotes dropped by RQ's counter; regests, introduction and registers not taken.",
    coverage="%d document files listed in mets.xml (the introduction counts 154 documents); see problems for files that could not be downloaded." % len(files), problems=problems))
