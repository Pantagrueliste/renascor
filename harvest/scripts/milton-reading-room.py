import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys; sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
import re, urllib.parse, json
from lxml import html as LH
h = Harvest("milton-reading-room")
B = "https://www.milton.host.dartmouth.edu/reading_room/"
EXCL = re.compile(r"(^|/)(intro|introduction|note|notes|bibliography|links|copyrights|contents|frontispiece)(/|\.|$)|intro\.shtml|\.(jpg|png|gif|pdf)$", re.I)
def rel_of(u): return u.replace(B, "")
def get_page(u):
    return h.get(u, "files/" + re.sub(r"[^A-Za-z0-9._-]+", "_", rel_of(u)))
toc = get_page(B + "contents/text.shtml")
queue = []
def push(u):
    u = u.split("#")[0]
    if not u.startswith(B): return
    r = rel_of(u)
    if EXCL.search(r) or not re.search(r"\.s?html?$", r): return
    if u not in queue: queue.append(u)
for a in LH.fromstring(toc).xpath("//a[@href]"):
    push(urllib.parse.urljoin(B + "contents/", a.get("href")))
i = 0
while i < len(queue):
    u = queue[i]; i += 1
    s = LH.fromstring(get_page(u))
    for a in s.xpath("//div[@id='sidebar']//a[@href]"):
        push(urllib.parse.urljoin(u, a.get("href")))
# year by path
def year_of(r):
    p = r.split("/")
    d = p[0]
    if d == "pl": return 1674
    if d in ("pr", "samson"): return 1671
    PROSE = {"of_reformation": 1641, "of_prelatical": 1641, "animadversions": 1641, "reason": 1642, "apology": 1642, "ddd": 1644, "bucer": 1644,
             "tetrachordon": 1645, "colasterion": 1645, "of_education": 1644, "areopagitica": 1644, "tenure": 1650, "eikonoklastes": 1650,
             "a_defence": 1658, "britain": 1671, "civil_power": 1659, "readie_and_easie_way": 1660, "prolusions": 1674}
    if d in PROSE: return PROSE[d]
    if d == "private_letters":
        m = re.search(r"(1[67]\d\d)", urllib.parse.unquote(r)); return int(m.group(1)) if m else 1674
    if d == "sonnets":
        m = re.search(r"sonnet_(\d+)", r)
        return 1645 if (not m or int(m.group(1)) <= 12) else 1673
    if d in ("fair_infant", "fifth_ode", "vacation", "conscience", "psalms", "apologus", "effigy", "rouse", "1673", "carmina", "ignavus"): return 1673
    return 1645
STOP = {"en": set("the and of to in that is with for his they their which this from but not are was be by as or all he him her had have shall will thou thee thy".split()),
        "la": set("et in est non cum quae quod ad ut sed per ab ex qui quam enim nec aut sit sunt esse hoc ille iam tamen".split()),
        "it": set("di che e il la per un una non con le del della si come ma più sono ch'io mi io tu sì".split())}
def lang_of(text):
    if len(re.findall(r"[Ͱ-Ͽἀ-῿]", text)) > 0.3 * max(1, len(text)) * 0.6: return "Greek"
    toks = re.findall(r"[a-zà-ÿ']+", text.lower())
    if not toks: return "English"
    sc = {k: sum(w in v for w in toks) / len(toks) for k, v in STOP.items()}
    best = max(sc, key=sc.get)
    return {"en": "English", "la": "Latin", "it": "Italian"}[best]
probs = []; n_empty = []
for u in queue:
    r = rel_of(u)
    s = LH.fromstring(get_page(u))
    c = s.xpath("//div[@id='content']")
    if not c:
        n_empty.append(r); continue
    e = c[0]
    for bad in e.xpath(".//*[contains(@class,'line')][self::span]|.//script|.//style"):
        bad.tail = (" " + (bad.tail or ""))
        bad.drop_tree()
    for br in e.xpath(".//br"):
        br.tail = "\n" + (br.tail or "")
    for p in e.xpath(".//p|.//div|.//blockquote|.//h1|.//h2|.//h3|.//h4"):
        p.tail = "\n" + (p.tail or "")
    text = e.text_content()
    text = "\n".join(re.sub(r"[ \t\r\xa0]+", " ", l).strip() for l in text.splitlines())
    text = re.sub(r"\n{2,}", "\n", text).strip()
    if len(text.split()) < 3:
        n_empty.append(r); continue
    lang = lang_of(text)
    h.add(re.sub(r"[^A-Za-z0-9._-]+", "_", r.replace("/text.shtml", "").replace(".shtml", "")) + ".txt", text, language=lang, year=year_of(r),
          source=f"Milton Reading Room: {r}", url=u)
if n_empty: probs.append(f"{len(n_empty)} pages without a text body skipped: {n_empty}")
probs += ["Text taken from div#content of each page (original spelling of the 17th-c. printings; hover glosses are title attributes and not included; line-number markers removed). Editorial introductions, 'Note on the text', bibliographies, links and the separate annotation layer (div#annotation) excluded.",
 "Years are by volume/work as stated in the table of contents (1641-1674 for prose, 1645/1673 for the shorter poems, sonnets split at no. 12, 1671 for Paradise Regain'd/Samson, 1674 for Paradise Lost) and approximate; all fall inside 1450-1700 anyway. 'A Defence of the English People' is the Latin Defensio (site gives 1658; first edition 1651).",
 "Language guessed from function words per page (Latin/Italian/Greek poems, Latin letters/prolusions); mixed pages may be mislabelled. Site licence CC BY-ND 3.0; copyright page reserves the XHTML coding and editorial material (only the period text is kept here). The 'Editing still in progress' note applies to the Defence."]
rep = h.finish(method="Crawled the contents page and the sidebar navigation of each work (about 1 request per page, 1 s apart); no bulk export exists.", coverage="All text pages reachable from the contents page (whole poetry, prose works, letters, prolusions); introductions and apparatus excluded.", problems=probs)
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"], rep["language_words"])
