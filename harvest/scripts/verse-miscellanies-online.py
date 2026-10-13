import os as _os; HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
sys.path.insert(0, HARVEST_DIR)
from hlib import Harvest, tei_year, first_year, slug
import re, json, time, urllib.parse
from bs4 import BeautifulSoup

h = Harvest("verse-miscellanies-online", delay=1.5)
problems = []
HOST = "versemiscellaniesonline.bodleian.ox.ac.uk"
EDITIONS = {  # url slug -> (title, year)
    "tottels-miscellany": ("Tottel's Miscellany", 1557),
    "handful-of-pleasant-delights": ("A Handful of Pleasant Delights", 1566),
    "paradise-of-dainty-devises": ("The Paradise of Dainty Devices", 1576),
    "gorgeous-gallery": ("The Gorgeous Gallery of Gallant Inventions", 1578),
    "phoenix-nest": ("The Phoenix Nest", 1593),
    "englands-helicon": ("England's Helicon (1600)", 1600),
    "englands-helicon-1614": ("England's Helicon (1614)", 1614),
    "poetical-rhapsody": ("A Poetical Rhapsody", 1602),
}

def wb_get(url, rel, tries=5):
    """Polite fetch from the Wayback Machine with back-off on 429/5xx."""
    for i in range(tries):
        try:
            return h.get(url, rel)
        except Exception as e:
            msg = str(e)
            if any(c in msg for c in ("429", "500", "502", "503", "504", "Timeout", "Connection")):
                time.sleep(20 * (i + 1)); continue
            raise
    raise RuntimeError("gave up: " + url)

# 1. CDX listing of captures (cached)
cdx_rel = "files/cdx.json"
if (h.dir / cdx_rel).exists():
    rows = json.loads((h.dir / cdx_rel).read_text())
else:
    q = ("https://web.archive.org/cdx/search/cdx?url=" + HOST + "&matchType=prefix&output=json"
         "&fl=timestamp,original,mimetype,statuscode&filter=statuscode:200&filter=mimetype:text/html&limit=50000")
    rows = json.loads(wb_get(q, cdx_rel))
rows = rows[1:]
cap = {}   # lowercase path -> (timestamp, original url)
for ts, u, m, s in rows:
    p = re.sub(r"^https?://[^/]+(:80)?", "", u).split("?")[0].split("#")[0].lower()
    if not p.startswith("/texts/"):
        continue
    if p not in cap or ts > cap[p][0]:
        cap[p] = (ts, u)

def raw_url(ts, u):
    return f"https://web.archive.org/web/{ts}id_/{u}"

def leaf_paths(ed):
    pre = f"/texts/{ed}/"
    return sorted(p for p in cap if p.startswith(pre) and p.count("/") == 4 and p.endswith("/")
                  and "embed" not in p)

# 2. expected leaves: the captured leaf pages plus every leaf they name as Previous/Next (the site's own page chain)
expected = {ed: set() for ed in EDITIONS}

def extract(html):
    s = BeautifulSoup(html, "lxml")
    t = s.select_one("div.entry-content div.text") or s.select_one("div.text")
    if not t:
        return None
    for sel in (".editorialNote", ".editorialNoteExpand", ".glossNote", ".choiceNote", ".linenumber", "script", "style", ".navigation"):
        for x in t.select(sel):
            x.decompose()
    for br in t.find_all("br"):
        br.replace_with(" ")
    # keep one line per verse line / heading / paragraph
    out = []
    for el in t.select("h3, h4, h2, .l, p, .stage, .sp"):
        if el.find_parent(class_="l") is not None and "l" not in (el.get("class") or []):
            continue
        txt = re.sub(r"\s+", " ", el.get_text(" ", strip=True))
        txt = re.sub(r"\s+([,.;:!?])", r"\1", txt)
        if txt:
            out.append(txt)
    if not out:
        out = [re.sub(r"\s+", " ", t.get_text(" ", strip=True))]
    return "\n".join(out)

stats = {}
for ed, (title, year) in EDITIONS.items():
    leaves = leaf_paths(ed)
    got = skipped_empty = 0
    for p in leaves:
        ts, u = cap[p]
        try:
            html = wb_get(raw_url(ts, u), f"files/{ed}/{slug(p.strip('/').split('/')[-1])}.html")
        except Exception as e:
            problems.append(f"{p}: {str(e)[:80]}"); continue
        for a in BeautifulSoup(html, "lxml").select("div.navigation a[href]"):
            nm = a["href"].split("#")[0].strip("/").split("/")[-1].lower()
            if nm and nm not in ("index", "embed") and a.get_text(strip=True) in ("Previous", "Next"):
                expected[ed].add(f"/texts/{ed}/{nm}/")
        txt = extract(html)
        if not txt or len(txt.split()) < 5:
            skipped_empty += 1; continue
        leaf = p.strip("/").split("/")[-1]
        h.add(f"{ed}__{leaf}.txt", txt, language="English", year=year,
              source=f"Verse Miscellanies Online: {title}, {leaf}", url=raw_url(ts, u))
        got += 1
    expected[ed] |= set(leaves)
    stats[ed] = (len(leaves), len(expected[ed]), len(expected[ed] & set(leaves)), got, skipped_empty)

lines = []
for ed, (nl, ne, ninter, got, emp) in stats.items():
    lines.append(f"{ed}: {nl} leaf pages captured, {ne} in the page chain (captured pages plus the leaves they link to as Previous/Next) ({ninter} captured), {got} with text, {emp} empty/non-text")
tot_exp = sum(v[1] for v in stats.values()); tot_int = sum(v[2] for v in stats.values())
share = f"{100*tot_int/tot_exp:.0f}%" if tot_exp else "n/a"

rep = h.finish(
    method="Listed captures with the Wayback CDX API (prefix query on the host, status 200, text/html), kept the latest capture of each leaf page /texts/<edition>/<leaf>/, fetched the raw capture (id_ form, no Wayback toolbar) at 1.5 s intervals and extracted the div.text of each leaf (original-spelling text with editor's regularisation of abbreviations); the site's editorial notes, glosses, abbreviation-expansion notes and line numbers were removed. One record per leaf page (signature) of each edition.",
    coverage="Captured share of the leaf pages of the editions (denominator = captured leaves plus leaves named by Previous/Next links; the capture of the tables of contents was unusable): " + share + f" ({tot_int} of {tot_exp}). Per edition: " + "; ".join(lines) + ". Contexts, glossary, index and working-paper pages excluded (modern).",
    problems=problems + [
        "Records are leaves (signatures), not poems: poems running across a leaf break are split between records.",
        "The text is the EEBO-TCP transcription with light regularisation by the editors (normalised spelling/abbreviations, accepted).",
        "Poetical Rhapsody is barely captured by the Wayback Machine.",
        "Paradise of Dainty Devices is a collated edition of 1576-1580 (dated 1576).",
    ])
print(rep)
