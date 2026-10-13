import os as _os; HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
sys.path.insert(0, HARVEST_DIR)
from hlib import Harvest, tei_year, first_year, slug
import re, zipfile, html

h = Harvest("london-lives-1690-1800")
problems = []
# Bulk XML of the project (CC BY-NC 4.0), referenced from the site's Licensing and Citation Guide
ZIP_URL = "https://ndownloader.figshare.com/files/7889602"   # figshare article 4797829, LL_XML_1-1.zip (89 MB)
zpath = h.dir / "files" / "LL_XML_1-1.zip"
if not zpath.exists():
    h.get(ZIP_URL, "files/LL_XML_1-1.zip", binary=True)

LO_Y, HI_Y = 1690, 1700
DATE = re.compile(r'<date\b[^>]*\bmodern="(\d\d)\.(\d\d)\.(\d{4})"')
IMG = re.compile(r"<img>([^<]*)</img>")
TAG = re.compile(r"<[^>]+>")
META_DATES = re.compile(r'<elementDate>(.*?)</elementDate>', re.S)

def years_of(s):
    return [int(m.group(3)) for m in DATE.finditer(s) if m.group(3) != "0000"]

zf = zipfile.ZipFile(zpath)
names = sorted(n for n in zf.namelist() if n.endswith(".xml") and "__MACOSX" not in n and "/XMLfiles/" in "/" + n)
n_files = len(names); n_overlap = 0; n_pages_seen = 0
by_series = {}
for n in names:
    raw = zf.read(n).decode("utf-8", errors="replace")
    md = META_DATES.search(raw)
    fy = years_of(md.group(1)) if md else []
    if fy and (min(fy) > HI_Y or max(fy) < LO_Y):
        continue                      # whole file outside 1690-1700
    n_overlap += 1
    fid = n.rsplit("/", 1)[-1][:-4]
    series = fid[2:4] if len(fid) > 4 else fid
    body = raw[raw.find("<transcript"):] if "<transcript" in raw else raw
    parts = IMG.split(body)           # [pre, img1, text1, img2, text2, ...]
    cur = min(fy) if fy else None
    units = [("p0", parts[0])] + [(parts[i], parts[i + 1]) for i in range(1, len(parts) - 1, 2)]
    for img, seg in units:
        n_pages_seen += 1
        ys = years_of(seg)
        if ys:
            cur = ys[0]
        if cur is None or not (LO_Y <= cur <= HI_Y):
            continue
        txt = html.unescape(TAG.sub(" ", seg.replace("<lb/>", " ").replace("<hr/>", " ")))
        txt = re.sub(r"[ \t]+", " ", re.sub(r"\s*\n\s*", "\n", txt)).strip()
        if not txt or len(txt.split()) < 3:
            continue
        fname = f"{fid}_{img.strip() or 'p0'}"
        if fname in h.seen:
            fname += f"_{len(h.seen)}"
        h.add(fname + ".txt", txt, language="English", year=cur,
              source=f"London Lives, {fid} (series {series})", url="https://www.londonlives.org/record/" + (img.strip() or fid))
        by_series[series] = by_series.get(series, 0) + 1

rep = h.finish(
    method="Downloaded the project's own bulk XML (figshare 4797829, LL_XML_1-1.zip, CC BY-NC 4.0, 1,624 files), referenced from the Licensing and Citation Guide of the site (non-commercial/linguistic analysis is explicitly permitted; no generative-AI training use). Read the zip in place, skipped files whose elementDate range lies outside 1690-1700, split the others into pages at the <img> facsimile markers, dated each page by its first <date modern=...> (otherwise the previous page's date, otherwise the file's start date) and kept pages dated 1690-1700. Tags were stripped; names, places and marginalia kept as part of the manuscript text.",
    coverage=f"Pages dated 1690-1700 from {n_overlap} of {n_files} XML files whose date range overlaps 1690-1700; {len(h.records)} pages kept out of {n_pages_seen} pages in the overlapping files. Per series (page counts): {by_series}. Source is the 2017 XML release (version 1), not the 2025 site version 3.0, so later additions are missing.",
    problems=problems + [
        "Page dates are inferred (first dated entry on the page, else carried forward from the previous page); a minority of pages in long volumes spanning many years may be mis-dated, and undated items are lost.",
        "Mixed old/new style and 00.00.yyyy partial dates were read by year only.",
        "The XML contains diplomatic transcriptions, with some printed material (Old Bailey Proceedings, Ordinary's Accounts) transcribed normally; tabular records (poll tax, registers) are mostly names and figures.",
        "Terms of use: CC BY-NC 4.0; the site forbids use for training generative AI, so the staging text must be used for counting/analysis only.",
        "The 2025 site (version 3.0) has more material than the 2017 XML release.",
    ])
print(rep)
