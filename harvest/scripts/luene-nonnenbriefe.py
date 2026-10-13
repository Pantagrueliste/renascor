import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import re
import sys
from collections import Counter
HD = HARVEST_DIR + ""
sys.path[:0] = [HD, HD + "/scripts"]
from hlib import Harvest, first_year  # noqa: E402
import hab  # noqa: E402

RID = "luene-nonnenbriefe"
ED = "ed000248"
problems = []
h = Harvest(RID)
files = [p for p in hab.mets_files(h, ED, prefix="texts/") if re.match(r"texts/Brief\d+", p)]
odd = []
undated = 0
langs = Counter()
for p in files:
    data = hab.fetch(h, ED, p, problems)
    if data is None:
        continue
    root = hab.parse(data)
    # year: sent date in correspDesc, else a year in the title
    year = None
    for ca in root.iter("{*}correspAction"):
        if ca.get("type") == "sent":
            for d in ca.iter("{*}date"):
                year = first_year(d.get("when") or d.get("notBefore") or d.get("from") or "".join(d.itertext()))
    if year is None:
        year = first_year(hab.title_of(root))
    if year is not None and not (1450 <= year <= 1700):
        odd.append((p, year))
        year = None
    tl = root.find(".//{*}textLang")
    code = tl.get("mainLang") if tl is not None else None
    lang = hab.lang_name(code, "Low German")
    langs[lang] += 1
    hab.normalise(root)  # original spelling (orig) kept, regularised (reg) dropped
    undated += year is None
    h.add(p.split("/")[-1], hab.serialise(root), language=lang, year=year, dateless_in_window=True,
          source="Netzwerke der Nonnen, Briefsammlung Kloster Lüne (Hs. 15), HAB Wolfenbüttel", url=hab.HAB + ED + "/" + p)
if odd:
    problems.append("year outside 1450-1700 in header/title, treated as undated (project dates the collection c. 1460-1555): " + ", ".join(f"{a.split('/')[-1]}={b}" for a, b in odd))
problems.append(f"{undated} of {len(files)} letters undated: year=None with dateless_in_window=True, since the project dates the whole collection c. 1460-1555; languages by textLang mainLang: {dict(langs)}")
print(h.finish(
    method="Letter transcription files (texts/BriefNNN-*_tei-transcript.xml) listed in mets.xml, fetched one by one; original-spelling reading kept (orig), regularisation (reg) and critical-apparatus notes dropped; introduction, bibliography and register not taken.",
    coverage="all: %d letter files listed in mets.xml (work in progress edition, files as of harvest date)." % len(files), problems=problems))
