import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import re
import sys
from collections import Counter
HD = HARVEST_DIR + ""
sys.path[:0] = [HD, HD + "/scripts"]
from hlib import Harvest, first_year  # noqa: E402
import hab  # noqa: E402

RID = "rubens-online"
ED = "ed000083"
problems = []
h = Harvest(RID)
files = [p for p in hab.mets_files(h, ED) if p.startswith(("archivalien/", "viten/"))]
src_year = Counter()
divtypes = Counter()
for p in files:
    data = hab.fetch(h, ED, p, problems)
    if data is None:
        continue
    root = hab.parse(data)
    year = None
    how = None
    for d in root.iter("{*}origDate"):
        year = first_year(d.get("when") or d.get("notBefore") or d.get("from") or "".join(d.itertext()))
        if year:
            how = "origDate"
            break
    if year is None:
        for b in root.iter("{*}listBibl"):
            y = first_year(" ".join(b.itertext()))
            if y:
                year, how = y, "bibl"
                break
    if year is None:
        year, how = first_year(p.split("/")[-1]), "filename"
    if year is None:
        year = first_year(hab.title_of(root)); how = "title"
    src_year[how] += 1
    for d in root.iter("{*}div"):
        divtypes[d.get("type")] += 1
    hab.normalise(root)
    lang = hab.dominant_lang(root, None)
    if lang is None:
        body = hab.body_el(root)
        lang = hab.guess_lang(hab.plain(body) if body is not None else "", "Dutch")
        problems.append(f"{p}: no xml:lang in text, language guessed")
    if year is None:
        problems.append(f"{p}: no year found")
    h.add(p.split("/")[-1], hab.serialise(root), language=lang, year=year,
          source="Rubens-online, HAB Wolfenbüttel", url=hab.HAB + ED + "/" + p)
problems.append(f"year source: {dict(src_year)}; div types seen: {dict(divtypes)}")
problems.append("Codex diplomaticus Rubenianus (cdr/), registers, translation and metadata files not taken; texts dated after 1700 are in staging with their year and fall outside the window")
print(h.finish(
    method="TEI files under archivalien/ and viten/ listed in mets.xml, fetched one by one; year from origDate, else bibliographic data, else file name; language from xml:lang on the text divisions.",
    coverage="all archival records, letters and printed texts listed in mets.xml (%d files); cdr/ (Codex diplomaticus) excluded." % len(files), problems=problems))
