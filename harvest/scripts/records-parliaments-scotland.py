import os as _os; HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, html, json
sys.path.insert(0, HARVEST_DIR)
from hlib import Harvest, tei_year, first_year, slug

BASE = "https://www.rps.ac.uk/search.php"
MAX_REQ = 20000
# (fn, first id) of the manuscript (original-language) text of each reign; the index of a reign lists every record.
REIGNS = [("jamesii_ms", 2592), ("jamesiii_ms", 4111), ("jamesiv_ms", 5994), ("jamesv_ms", 7423),
          ("maryi_ms", 8819), ("jamesvi_ms", 12767), ("charlesi_ms", 25094), ("charlesii_ms", 40588),
          ("jamesvii_ms", 47762), ("william_and_mary_ms", 51238), ("williamii_ms", 57659)]
h = Harvest("records-parliaments-scotland", delay=3)  # 3 s agreed with the RPS team (2026-10-14); robots.txt asks 20 s
reqs = 0

def fetch(url, rel):
    global reqs
    if not (h.dir / rel).exists():
        reqs += 1
    return h.get(url, rel)

def text_of(s):
    s = re.sub(r"(?s)<(script|style)\b.*?</\1>", " ", s)
    s = re.sub(r"<(br|/p|/div|/li|/h\d)\b[^>]*>", "\n", s)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    s = re.sub(r"[ \t\xa0]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()

# 1. indexes
leaves = []
for fn, rid in REIGNS:
    ix = fetch(f"{BASE}?action=fetch_index&fn={fn}&id={rid}&query=&type=ms", f"index/{fn}.html")
    year = None
    for m in re.finditer(r'(?s)(<a href="#" onclick="return t\([^>]*>\s*<img[^>]*>\s*</a>\s*)?<a href="search\.php\?a=fcf&amp;fn=(\w+)&amp;id=(\d+)&amp;t=ms"[^>]*>(.*?)</a>', ix):
        expandable, f, i, label = m.group(1), m.group(2), int(m.group(3)), html.unescape(m.group(4)).strip()
        if expandable:
            y = re.match(r"(\d{4}),", label)
            if y:
                year = int(y.group(1))
            continue
        if year is not None and 1450 <= year <= 1700:
            leaves.append((f, i, year, label))
n_all = len(leaves)
budget = MAX_REQ - len(REIGNS) - 5
if n_all > budget:
    sel = [leaves[int(k * n_all / budget)] for k in range(budget)]
else:
    sel = leaves
print("records in window", n_all, "selected", len(sel), "index requests", reqs, flush=True)
json.dump(leaves, open(h.dir / "leaves.json", "w"))

# 2. records
def extract(page):
    m = re.search(r"(?s)\[\s*print\s*\].*?\[\s*email\s*\].*?\[\s*cite\s*\](.*?)(?:View page in frame set|$)", page.replace("</a>", "</a>"))
    body = page
    t = text_of(body)
    k = t.find("[cite]")
    if k >= 0:
        t = t[k + 6:]
        k2 = t.find("[following]")
        if k2 >= 0 and k2 < 80:
            t = t[k2 + 11:]
    t = t.split("View page in frame set")[0]
    return t.strip()

LAT = set("et ac in quod regni nostri domini dei regis cum de pro per ad sunt est qui que presentes anno die mense ipsius eiusdem predicti predicte sue sui suis".split())
FR = set("le la les du des est que qui roy royaume sont aux avec pour par dans".split())
SC = set("the and of be at sall to that ar thai thair haf quhilk ane bot or with for is it his our oure in as".split())
def guess_lang(t):
    w = re.findall(r"[a-z']+", t.lower())
    a, b, c = (sum(x in S for x in w) for S in (LAT, FR, SC))
    if a > b and a > c: return "Latin"
    if b > a and b > c: return "French"
    return "Scots"

for f, i, year, label in sel:
    try:
        page = fetch(f"{BASE}?action=fc&fn={f}&id={i}&query=&type=ms&variants=&google=", f"rec/{f}_{i}.html")
    except Exception as e:
        print("fail", f, i, e, flush=True); continue
    raw = extract(page)
    if len(raw) < 30:
        continue
    lang = guess_lang(raw)
    h.add(f"{f}_{i}.txt", raw, language=lang, year=year, source="Records of the Parliaments of Scotland",
          url=f"https://www.rps.ac.uk/frameset.php?id={i}&type=ms&filename={f}")

pct = round(100 * len(sel) / max(n_all, 1), 1)
rep = h.finish(method="Reign indexes (11 requests) parsed for record ids; one request per record page (search.php?action=fc, manuscript text only); 3 s delay agreed with the RPS team (robots.txt asks 20 s).",
    coverage=(f"All {n_all} manuscript records dated 1450-1700 listed in the reign indexes, James II to William II." if len(sel) == n_all else f"Record-level systematic sample: {len(sel)} of {n_all} manuscript records dated 1450-1700 ({pct}%), spread evenly over all reigns from James II to William II, stopped at the {MAX_REQ}-request cap. Not exhaustive."),
    problems=["Site has no bulk download or API; one page per record.",
              "Language is guessed per record from word frequencies (Latin, French or Scots); records mix Latin, French and Scots, and some carry short English editorial headings.",
              "Records in English editorial summary form (non-parliamentary items) may be included."])
print(rep["texts_in_window"], rep["words_in_window"])
