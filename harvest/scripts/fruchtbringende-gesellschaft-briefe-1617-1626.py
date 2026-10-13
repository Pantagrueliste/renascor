import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import re
import sys
HD = HARVEST_DIR + ""
sys.path[:0] = [HD, HD + "/scripts"]
from hlib import Harvest  # noqa: E402
import hab  # noqa: E402

RID = "fruchtbringende-gesellschaft-briefe-1617-1626"
ED = "ed000213"
problems = []
h = Harvest(RID)
files = hab.mets_files(h, ED, prefix="briefe/")
n_fallback = 0
for p in files:
    data = hab.fetch(h, ED, p, problems)
    if data is None:
        continue
    root = hab.parse(data)
    hab.normalise(root)
    body = hab.body_el(root)
    content = [d for d in root.iter("{*}div") if d.get("type") == "content"]
    if body is not None and content:
        c = content[0]
        for hd in c.findall("{*}head"):  # editorial heading "Text"
            c.remove(hd)
        for k in list(body):
            body.remove(k)
        body.append(c)
    else:
        n_fallback += 1
        problems.append(f"{p}: no div type=content, whole body kept")
    m = re.match(r"(\d\d)(\d\d)(\d\d)", p.split("/")[-1])
    year = 1600 + int(m.group(1)) if m else None
    if year is None:
        problems.append(f"{p}: year not derivable from file name")
    lang = hab.dominant_lang(root, "German")
    h.add(p.split("/")[-1], hab.serialise(root), language=lang, year=year,
          source="Briefe der Fruchtbringenden Gesellschaft 1617-1626, HAB Wolfenbüttel", url=hab.HAB + ED + "/" + p)
problems.append("catalogue estimate of 101,000 words evidently includes the editorial summaries, source descriptions and commentary; only the letter text itself is staged (about 48,000 words)")
print(h.finish(
    method="Letter files (briefe/*.xml) listed in mets.xml, fetched one by one; only the letter text (div type=content) is kept: editorial summary, source description, address block and commentary dropped. Year = 1600 + the two leading digits of the file name (YYMMDD).",
    coverage="all: %d letter files listed in mets.xml of Band 1 (1617-1626)." % len(files), problems=problems))
