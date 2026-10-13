import os as _os; HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
sys.path.insert(0, HARVEST_DIR)
from hlib import Harvest, tei_year, first_year, slug
import csv, zipfile, io, html, re, collections

csv.field_size_limit(10**9)
h = Harvest("open-source-shakespeare", delay=10)  # robots.txt Crawl-delay: 10
problems = []
url = "https://www.opensourceshakespeare.org/downloads/oss-textdb.zip"
data = h.get(url, "files/oss-textdb.zip", binary=True)
z = zipfile.ZipFile(io.BytesIO(data))

def rows(name):
    txt = z.read(name).decode("utf-8", errors="replace")
    return list(csv.DictReader(io.StringIO(txt, newline=""), quotechar="~"))

works = rows("Works.txt")
chars = {r["CharID"]: r["CharName"] for r in rows("Characters.txt")}
paras = collections.defaultdict(list)
for p in rows("Paragraphs.txt"):
    paras[p["WorkID"]].append(p)

def clean(s):
    s = html.unescape(s)
    s = s.replace("[p]", "\n")
    return "\n".join(l.rstrip() for l in s.splitlines() if l.strip())

for w in works:
    wid = w["WorkID"]
    ps = sorted(paras.get(wid, []), key=lambda p: int(p["ParagraphNum"]))
    out = []
    for p in ps:
        t = clean(p["PlainText"])
        if not t:
            continue
        who = chars.get(p["CharID"], "")
        out.append((who.upper() + "\n" if who and p["CharID"] != "xxx" else "") + t)
    raw = "\n\n".join(out)
    if not raw:
        problems.append(f"{wid}: no paragraphs")
        continue
    h.add(f"{wid}.txt", raw, language="English", year=first_year(w["Date"]),
          source=f"Shakespeare, {w['LongTitle'] or w['Title']} (Globe edition, OSS)", url="https://www.opensourceshakespeare.org/views/" )
problems.append("Year = the site's approximate composition date (Works.Date) for each work, not a publication date; The Passionate Pilgrim (1598/1599) and A Lover's Complaint (1609) are included as the site lists them. Texts are modernised spelling (Globe edition, via Moby/Gutenberg), kept as accepted. Speaker names (from Characters table) are prefixed to speeches and counted as words.")
problems.append("Site lists 43 works; the database holds %d works." % len(works))
rep = h.finish(method="Downloaded the site's own oss-textdb.zip (delimited text tables, CC BY-NC 4.0, one request, robots.txt Crawl-delay 10 respected) and rebuilt each work from Paragraphs.txt in paragraph order, with HTML entities decoded and [p] line markers turned into line breaks. One record per work.",
    coverage="All works in the database (plays, sonnets and poems); concordance, word forms and statistics tables were not used.",
    problems=problems)
print(rep)
