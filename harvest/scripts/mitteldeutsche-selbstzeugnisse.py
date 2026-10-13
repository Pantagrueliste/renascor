import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, urllib.parse, collections, time
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
from bs4 import BeautifulSoup
HD = HARVEST_DIR + ""
h = Harvest("mitteldeutsche-selbstzeugnisse", delay=1.2)
# 1. capture list from the Wayback CDX API (saved once to mdsz_cdx.txt)
rows = [l.split() for l in open(HD + "/mdsz_cdx.txt")]
caps = collections.defaultdict(list)
for ts, u, sc in rows:
    if "show_search_seite.php" in u or "show_sz.php" in u:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(u.replace("&amp;", "&")).query)
        if q.get("szid") and q.get("nr") and q["nr"][0].isdigit():
            caps[(q["szid"][0], int(q["nr"][0]))].append((ts, u))
print(len(caps), "distinct (szid, page) with captures")
NAMES = {"10": "Volkmar Happe, Chronicon Thuringiae", "20": "Michael Heubel", "30": "Hans Krafft", "40": "Caspar Heinrich Marx"}
pages = {}
miss = 0
for key in sorted(caps, key=lambda k: (k[0], k[1])):
    got = None
    for ts, u in sorted(set(caps[key]), reverse=True)[:3]:
        rel = f"files/wb/{key[0]}_{key[1]:04d}_{ts}.html"
        s = None
        for attempt in range(4):
            try:
                s = h.get(f"https://web.archive.org/web/{ts}id_/{u}", rel); break
            except Exception as e:
                code = getattr(getattr(e, "response", None), "status_code", None)
                if code in (404, 403): break
                time.sleep(30 * (attempt + 1))
        if s is None: continue
        if "Time out" in s or 'class="content"' not in s:
            continue
        got = s; break
    if got is None: miss += 1; continue
    pages[key] = got
print(len(pages), "usable pages;", miss, "keys without a usable capture")

BOLD = re.compile(r"\[(\d{4})(?:\.\d+)?\]")
bysz = collections.defaultdict(list)
for (szid, nr), html in pages.items():
    i = html.find('class="content"')
    body = html[i:]
    cut = body.find("<hr")
    body = body[: cut if cut > 0 else len(body)]
    body = re.sub(r"^class=\"content\">", "", body)
    soup = BeautifulSoup(body, "lxml")
    bs = [b for b in soup.find_all("b")][:3]
    head = " ".join(b.get_text(" ", strip=True) for b in bs)
    for b in bs: b.decompose()
    for a in soup.find_all("a"):
        if re.fullmatch(r"\[\w+\]", a.get_text(strip=True)) or "vorige Seite" in a.get_text() or "chste Seite" in a.get_text() or "Druckversion" in a.get_text():
            a.decompose()
    for br in soup.find_all("br"): br.replace_with("\n")
    t = soup.get_text("")
    m = BOLD.search(t)
    yr = int(m.group(1)) if m else None
    if yr is not None and not (1500 <= yr <= 1700): yr = None
    t = re.sub(r"^\s*[,;]?\s*f\.\s*\S+\s*", "", t)
    t = re.sub(r"\[\d{4}(?:\.\d+)?(?:\s*,\s*\d{4}(?:\.\d+)?)*\]", "", t, count=1)
    t = t.replace("\xa0", " ")
    t = re.sub(r"[ \t]+", " ", t); t = re.sub(r" ?\n ?", "\n", t); t = re.sub(r"\n{2,}", "\n", t).strip()
    bysz[szid].append((nr, head, yr, t))
print({k: len(v) for k, v in bysz.items()})
for szid in sorted(bysz):
    pl = sorted(bysz[szid])
    txt = "\n".join(p[3] for p in pl)
    yrs = [p[2] for p in pl if p[2]]
    name = NAMES.get(szid) or (pl[0][1].split(",")[0] if pl else szid)
    h.add(f"szid{szid}.txt", txt, language="German", year=(sorted(yrs)[len(yrs)//2] if yrs else None), dateless_in_window=True,
          source=f"MDSZ (Wayback copy 2019-2023), {name}: {len(pl)} manuscript pages recovered",
          url="https://web.archive.org/web/2022/http://mdsz.thulb.uni-jena.de/sz/", pages=len(pl),
          page_years=[min(yrs), max(yrs)] if yrs else None)
totp = sum(len(v) for v in bysz.values())
rep = h.finish(method="The original site is offline (domain serves an unrelated page). Used the Internet Archive: listed captured transcription pages (show_search_seite.php / show_sz.php with szid and page number nr) via the CDX API, fetched the newest usable capture of each page as raw id_ copy, kept only the transcription column (heading, page-date tag, footnote block and navigation removed; tooltip links flattened to text).",
  coverage="PARTIAL: %d manuscript pages recovered (of roughly 1,785 for Happe, 368 Heubel, 245 Krafft, 205 Marx plus unknown others per catalogue); only pages captured by the Wayback Machine, and ~40%% of captures are 'Time out' session error pages and were discarded. Recovered pages are concatenated per author (one record each)." % totp,
  problems=["Partial coverage as stated; counts are a lower bound.", "Page captures come from 2019-2023; the site's session timeouts made many captures empty.",
            "One record per manuscript author (szid): 10 Happe, 20 Heubel, 30 Krafft, 40 Marx; szid 25 and 45 are other items on the site if present.",
            "year = median of the page-date tags of the recovered pages (a few typos such as 1509 for Krafft appear in the page tags); all four authors wrote 1587-1684, inside the window, so dateless_in_window=True where no date was found."])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"])
