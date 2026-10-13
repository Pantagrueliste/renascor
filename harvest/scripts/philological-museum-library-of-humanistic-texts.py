import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, html, urllib.parse, requests
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year, slug
from bs4 import BeautifulSoup
h = Harvest("philological-museum-library-of-humanistic-texts")
HOST = "https://philological.cal.bham.ac.uk/"
def norm(u, base):
    u = urllib.parse.urljoin(base, u.strip())
    u = u.split("#")[0]
    u = re.sub(r"^https?://(www\.)?philological\.bham\.ac\.uk/", HOST, u)
    u = re.sub(r"^https?://philological\.cal\.bham\.ac\.uk/", HOST, u)
    return re.sub(r"(?<!:)/{2,}", "/", u)
def fetch(u):
    rel = "files/" + slug(u.replace(HOST, "")) 
    try:
        b = h.get(u, rel, binary=True)
    except requests.RequestException as e:
        return None
    # decode: try utf-8 then cp1252
    try: return b.decode("utf-8")
    except UnicodeDecodeError: return b.decode("cp1252", errors="replace")
lib = fetch(HOST + "library.html")
# the library page is served in utf-8 or latin-1; parse chunks per <br>
chunks = re.split(r"<br\s*/?>|</p>", lib)
works = {}
for c in chunks:
    anchors = re.findall(r'<a\s[^>]*href="([^"#][^"]*)"[^>]*>(.*?)</a>', c, re.S | re.I)
    anchors = [(norm(a, HOST), re.sub(r"<[^>]+>", "", t)) for a, t in anchors]
    anchors = [(a, t) for a, t in anchors if a.startswith(HOST) and not a.endswith(("analytic.html", "library.html"))]
    if not anchors: continue
    a, _ = max(anchors, key=lambda x: len(x[1]))
    label = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
    if a not in works: works[a] = label
EXC = re.compile(r"intro|trans|eng|comm|note|bibl|apparat|copyright|links|index|gloss|appar|crit|biog|abbrev|sigla|manuscr|preface|prefat|english|summary|argument|synopsis|contents|toc|mailto|fort|sources|testim|reception|stemma|textual", re.I)
LAT = set("et in est non ad quae quod cum qui ut sed ab ex per de se quam si nec sunt esse enim atque sit eius haec hoc nam tibi mihi tu te me quo".split())
ENG = set("the and of to in is that it was for with as his he by on be are this which not from at or an but have had her they were you".split())
def lang_score(t):
    w = re.findall(r"[a-zA-Z]+", t.lower())[:4000]
    if not w: return 0, 0
    return sum(x in LAT for x in w) / len(w), sum(x in ENG for x in w) / len(w)
def page_text(p):
    s = BeautifulSoup(p, "html.parser")
    for t in s(["script", "style", "a"]):
        if t.name != "a" or True: pass
    for t in s(["script", "style"]): t.decompose()
    for t in s.find_all("a"):
        if t.get("href", "").startswith("#") and len(t.get_text(strip=True)) < 4: t.decompose()  # footnote marks
    return re.sub(r"[ \t\r\f\v]+", " ", re.sub(r"\n\s*\n+", "\n\n", s.get_text("\n"))).strip()
n_fail = []; english_only = []; empty = []; seen_dirs = set()
for url, label in works.items():
    d = url if url.endswith("/") else url
    base = url if url.endswith("/") or url.endswith(".html") else url + "/"
    root = base if base.endswith("/") else base.rsplit("/", 1)[0] + "/"
    if root in seen_dirs and root != HOST: continue
    seen_dirs.add(root)
    idx = fetch(base)
    if idx is None:
        n_fail.append(url); continue
    pages = [base] if base.endswith(".html") else []
    cand = [base]
    # follow contents page(s)
    todo = [base]; visited = {base}; found = []
    for depth in range(2):
        nxt = []
        for pg in todo:
            t = idx if pg == base else fetch(pg)
            if not t: continue
            for l in re.findall(r'href="([^"#]+)', t):
                u = norm(l, pg)
                if not u.startswith(root) or u in visited or not re.search(r"\.html?$", u): continue
                visited.add(u)
                if re.search(r"contents|toc|index", u.rsplit("/", 1)[-1], re.I): nxt.append(u)
                else: found.append(u)
        todo = nxt
        if not todo: break
    if not found and base.endswith(".html"): found = [base]
    texts = []
    for u in found:
        name = u.replace(root, "")
        if EXC.search(name): continue
        p = fetch(u)
        if not p: continue
        t = page_text(p)
        la, en = lang_score(t)
        if en > la and en > 0.12: continue  # predominantly English: translation / commentary
        if len(t.split()) < 30: continue
        texts.append(t)
    if not texts:
        # works with only English (or no) period text
        empty.append(url); continue
    y = first_year(re.sub(r"^.*?\(", "(", label)) or first_year(label)
    raw = "\n\n".join(texts)
    la, en = lang_score(raw)
    lang = "Latin" if la >= en else "English"
    h.add(slug(root.replace(HOST, "")) + ".txt", raw, language=lang, year=y, source="Philological Museum: " + label[:100], url=root, label=label)
rep = h.finish(method="Parsed library.html for ~265 work entries, fetched each work's index/contents pages (robots.txt absent, 404), then every local HTML page except those named like introduction/translation/commentary/notes/bibliography/apparatus; pages whose text is predominantly English (stop-word test) were also dropped as translations/commentary. One record per work (pages concatenated). Year = first year in the library-page title (printed/composition date).",
  coverage=f"{len(works)} link targets in the library page; {len(h.records)} works harvested; {len(empty)} had no Latin/period page recognised; {len(n_fail)} failed to load.",
  problems=["Heuristic page selection: Latin text of some works may be missing, and some commentary pages may remain if named unusually or if mostly Latin","Works without a year in the title have year=None and dateless_in_window=False","Works with only English period text (some 17th-century English prose) are included only if the page is not predominantly English-by-stopwords: they are likely missing", f"no period page recognised: {empty[:60]}", f"failed to load: {n_fail[:40]}"])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"], len(empty), len(n_fail))
