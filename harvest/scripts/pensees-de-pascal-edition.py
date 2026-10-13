import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys; sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
import re, json, collections
import requests
from lxml import html as LH
h = Harvest("pensees-de-pascal-edition")
B = "https://www.penseesdepascal.fr/"
def page(rel):
    """Return page text or None for 404 (negative results cached as .404 markers)."""
    cache = "files/" + rel.replace("/", "__")
    if (h.dir / (cache + ".404")).exists():
        return None
    try:
        return h.get(B + rel, cache)
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            (h.dir / (cache + ".404")).write_text("")
            return None
        raise
# --- 1. fragment list from the liasse/dossier index pages
home = h.get(B, "files/index.html")
def links(html, base_rel):
    out = []
    for m in re.finditer(r'href="([^"#]+\.php)"', html):
        out.append(m.group(1))
    return out
import urllib.parse
idx = []
for l in links(home, ""):
    d = l.split("/")[0]
    if "/" in l and l.endswith(".php") and l.split("/")[-1][:-4] == d and l not in idx:
        idx.append(l)
known = set()
for l in idx:
    html = h.get(B + l, "files/" + l.replace("/", "__"))
    for x in links(html, l):
        u = urllib.parse.urljoin(B + l, x)[len(B):]
        m = re.match(r"^([^/]+)/(\1|[IVXL]+)?(\d+v?)-moderne\.php$", u) or re.match(r"^([^/]+)/([A-Za-z]+)(\d+v?)-moderne\.php$", u)
        if m: known.add((m.group(1), m.group(2), m.group(3)))
# directory -> filename stem
stem = {}
for d, st, n in known:
    stem[d] = st if st else d
nums = collections.defaultdict(set)
for d, st, n in known:
    nums[d].add(n)
def numpart(n): return int(re.match(r"\d+", n).group(0))
cands = []
for d in sorted(stem):
    mx = max(numpart(n) for n in nums[d])
    cands += [(d, n) for n in sorted(nums[d], key=lambda x: (numpart(x), x))]
    extra = [(d, str(i)) for i in range(1, mx + 1) if str(i) not in nums[d]]
    cands += extra
    # probe beyond the highest listed number
    i = mx + 1; miss = 0
    while miss < 2 and i < mx + 40:
        cands.append((d, str(i), "probe")); i += 1
        miss += 0  # decided while fetching
# --- 2. fetch savante pages
def extract(html):
    doc = LH.fromstring(html.encode("utf-8"))
    hs = [p for p in doc.xpath("//p") if "Transcription" in p.text_content() and "origine" in p.text_content()]
    if not hs:
        hs = [p for p in doc.xpath("//p") if re.search(r"Différences constatées|Transcription", p.text_content())]
    if not hs: return None, None, 0
    hp = hs[0]
    origin = re.sub(r"\s+", " ", hp.text_content()).strip()
    tbl = hp.xpath("following::table[1]")
    if not tbl: return origin, None, len(hs)
    cells = tbl[0].xpath(".//tr[1]/td") or [tbl[0]]
    for cell in cells:
        for sup in cell.xpath(".//sup"): sup.drop_tree()
        lines = []
        for p in cell.xpath(".//p"):
            s = re.sub(r"[\s\xa0]+", " ", p.text_content()).strip()
            if s: lines.append(s)
        if lines: return origin, "\n".join(lines), len(hs)
    return origin, None, len(hs)
def year_from(origin):
    o = origin or ""
    m = re.search(r"\b(16[5-9]\d|17\d\d)\b", o)
    if "Recueil des originaux" in o: return 1660
    if "Copies" in o or "copie" in o: return 1664
    if "1670" in o: return 1670
    if "1678" in o: return 1678
    if m: return int(m.group(1))
    return None
probs = []; stats = collections.Counter(); noext = []; multi = []
misses = collections.Counter(); skip_dirs = set()
for c in cands:
    d, n = c[0], c[1]
    probe = len(c) == 3
    if probe and d in skip_dirs: continue
    html = page(f"{d}/{stem[d]}{n}-savante.php")
    if html is None:
        if probe: skip_dirs.add(d)
        stats["404"] += 1; continue
    origin, text, nh = extract(html)
    if nh > 1: multi.append(f"{d}{n}")
    if not text:
        noext.append(f"{d}{n}"); continue
    y = year_from(origin)
    fn = f"{d}{n}.txt"
    h.add(fn, text, language="French", year=y if y else None, dateless_in_window=not y,
          source=f"Pascal, Pensées, {d} {n} - {origin}", url=B + f"{d}/{stem[d]}{n}-savante.php")
    stats[(origin or "")[:60]] += 1
if noext: probs.append(f"{len(noext)} savante pages with no extractable transcription (skipped): {noext[:40]}")
if multi: probs.append(f"{len(multi)} pages mention several transcription headings; only the first witness kept: {multi[:20]}")
probs += [
 "One record per fragment (liasse/dossier item): the 'Transcription savante' table of the fragment's -savante.php page (diplomatic transcription of the earliest witness: Recueil des originaux for most, Copies C1/C2, or Port-Royal 1670/1678 editions for fragments whose original is lost). Modernised text (-moderne.php), 'approfondir' commentary, notes column and the other witnesses (Copies, Port-Royal editions as separate transcriptions) were left out to avoid duplicating the same fragments.",
 "Year is the date of the witness: 1660 for Recueil des originaux (Pascal's papers, c. 1656-1662), 1664 for Copies C1/C2 (1662-1666), 1670/1678 for the Port-Royal editions, per the 'origine' line; approximate. Deleted words, insertions and manuscript layout are kept as in the transcription; superscript note numbers removed.",
 "Fragments are found through the liasse/dossier index pages plus probing of unlisted numbers of each series (pages not linked from the indexes exist, e.g. XXIII2); the Mémorial (Hors1) page has a different layout and is taken from its first table. Site copyright: all rights reserved (legal notice); used for counting only.",
 "Source pages classified by 'origine': " + json.dumps({k: v for k, v in stats.items() if k != '404'}, ensure_ascii=False)]
rep = h.finish(method="No bulk export; crawled the 38 liasse/dossier index pages and each fragment's -savante.php page (1 s between requests), probing numbers not linked from the indexes.",
  coverage="All fragments reachable by number in each series; text = one diplomatic transcription per fragment.", problems=probs)
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"], dict(stats))
