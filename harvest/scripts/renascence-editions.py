import os as _os; HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
sys.path.insert(0, HARVEST_DIR)
from hlib import Harvest, tei_year, first_year, slug
import re, urllib.parse
from bs4 import BeautifulSoup

BASE = "https://www.luminarium.org/renascence-editions/"
h = Harvest("renascence-editions")
problems = []

def rel_of(u):
    return "files/" + slug(u.replace("https://www.luminarium.org/", "")) + ".html"

def fetch(u):
    try:
        return h.get(u, rel_of(u))
    except Exception as e:
        problems.append(f"fetch failed {u}: {str(e)[:90]}")
        return None

def key(u):
    return u.replace(BASE, "")

index = h.get(BASE, "files/index.html")
soup = BeautifulSoup(index, "lxml")
top = []
for tr in soup.find_all("tr"):
    tds = tr.find_all("td", recursive=False)
    if len(tds) != 2:
        continue
    for a in tds[1].find_all("a", href=True):
        if re.search(r"scholarsbank|hdl\.handle|\.pdf$", a["href"]):
            continue
        u = urllib.parse.urljoin(BASE, a["href"]).split("#")[0]
        if u not in top:
            top.append(u)

# works whose index page links to chapter/part pages
PARENTS = {"fqintro.html", "lost/lost.html", "island/", "jones/jones.html", "hume/hume.html", "wealth/wealth.html",
           "gov/gov1.htm", "montaigne/index.htm", "walton/index.html", "swift/gulliver.html", "dryden/dryden2.html",
           "complaints.html", "shepheard.html", "courtier/courtier.html", "hobbes/leviathan.html", "proframe.html",
           "may/mayframe.html", "adv1.htm"}
SKIP = {"renchler.html", "may/550.html", "text.html", "milton.html", "renchler/", "browne/intro.html"}  # modern essays / editorial
parent_of = {}
pages = {}   # key -> html
queue = list(top)
seen = set(top)
while queue:
    u = queue.pop(0)
    k = key(u)
    if not u.startswith(BASE):
        if "luminarium.org" in u:
            problems.append(f"skipped page outside /renascence-editions/ (duplicate of a listed text): {u}")
        continue
    if k in SKIP:
        continue
    html = fetch(u)
    if html is None:
        continue
    pages[k] = html
    pk = parent_of.get(k)
    depth = 0
    p = k
    while p in parent_of:
        p = parent_of[p]; depth += 1
    if (k in PARENTS or (depth == 1 and re.match(r"montaigne/book[23]\.html", k))) and depth < 2:
        s = BeautifulSoup(html, "lxml")
        for a in s.find_all("a", href=True):
            c = urllib.parse.urljoin(u, a["href"]).split("#")[0]
            ck = key(c)
            if (not c.startswith(BASE) or c in seen or ck.endswith("ren.htm") or ck == k
                    or not re.search(r"\.html?$", ck) or "intro" in ck.split("/")[-1] or ck in SKIP):
                continue
            seen.add(c)
            parent_of[ck] = k
            queue.append(c)

# publication year of the work (not of the e-text); default = first year in the title block
YEAR = {
 "actors1.html":1643,"Emaricdulfe.html":1595,"barley.html":1607,"everyman.html":1521,"jest.html":1580,"key.html":1644,"ent.htm":1636,
 "tract2.html":1644,"spare.html":1555,"player2.html":1641,"triall.html":1654,"tract1.html":1644,"phoenix.html":1593,"ascham1.htm":1570,
 "adv1.htm":1605,"bacon.html":1625,"bacon3.html":1626,"ballads.html":1798,"barker1.html":1659,"beaumont1.html":1625,"beggar.html":1728,
 "berkeley.html":1710,"berners/berners.html":1496,"bf1.html":1613,"bill1.html":1775,"breton1.html":1604,"breton2.html":1605,
 "browne/medici.html":1643,"browne/hydriotaphia.html":1658,"browne/letter.html":1690,"bunyan1.html":1678,"coelia.html":1594,
 "colin.html":1595,"collins2.html":1742,"collins/collins1.html":1746,"complaints.html":1591,"comus.html":1637,"congress1.html":1775,
 "congreve1.html":1710,"congreve2.html":1700,"courtier/courtier.html":1561,"crusoe.html":1719,"curial.html":1484,"daniel2.html":1599,
 "daphna.html":1591,"davies1.html":1596,"defence.html":1595,"defoe3.html":1722,"dekker2.html":1609,"delia.html":1592,"yeare.html":1603,
 "diana.html":1594,"digger.html":1649,"donne1.html":1612,"donne2.html":1633,"drayton1.html":1595,"dryden1.html":1682,
 "dryden/dryden2.html":1697,"dudley1.html":1586,"edu.html":1644,"edwards1.html":1571,"eliz1.html":1601,"eliz2.html":1591,"eliz3.html":1569,
 "ellwood1.html":1714,"ester.htm":1617,"fbeaumont1.html":1602,"fqintro.html":1596,"goldsmith1.html":1770,"goldsmith2.html":1764,
 "gorboduc.html":1565,"gosson1.html":1579,"gov/gov1.htm":1531,"gray1.html":1751,"greene1.html":1592,"greene2.html":1594,"greene3.html":1591,
 "greene4.html":1592,"greene5.html":1592,"greene6.html":1592,"gresham1.html":1626,"guilpin.html":1598,"hallch.htm":1608,"heywood1.html":1613,
 "hobbes/leviathan.html":1651,"hume/hume.html":1748,"hunting/cockaine.html":1591,"hymnes.html":1596,"instructions.html":1776,
 "island/":1633,"james1.html":1604,"jane.html":1553,"johnson.html":1749,"jones/jones.html":1749,"jonson1.html":1605,"jonson2.html":1608,
 "jonson3.html":1611,"kemp.html":1600,"kind.html":1592,"kyd1.html":1592,"lanyer1.html":1611,"letters.html":1580,"locke2.html":1560,
 "lodge.html":1579,"lodge/lodge1.html":1590,"lost/lost.html":1667,"lycidas.html":1645,"marlowe1.html":1598,"marlowe2.html":1604,
 "marlowe3.html":1590,"marlowe4.html":1590,"mary.html":1621,"modest.html":1729,"montagu.html":1736,"montaigne/index.htm":1603,
 "mortal.htm":1621,"nashe1.html":1592,"oroonoko.html":1688,"parl1.html":1647,"peele1.html":1607,"phoenix.html":1593,"poesie.html":1602,
 "proframe.html":1596,"psalms.html":1673,"r3.html":1557,"rachel.html":1617,"raleigh1.html":1591,"raleigh2.html":1644,"readie.html":1660,
 "reason1.html":1794,"regained.html":1671,"rerum.html":1600,"roper1.html":1626,"rover1.html":1677,"rover2.html":1681,"ryme.html":1603,
 "samson.html":1671,"shepheard.html":1579,"smart1.html":1763,"smith1.html":1596,"sonnets.html":1592,"sotweed.htm":1708,"spain.html":1624,
 "steel/steel.html":1576,"stella.html":1591,"sterne.html":1768,"swift3.html":1721,"swift/gulliver.html":1726,"taylor1.html":1620,
 "taylor2.html":1618,"taylor3.html":1619,"thomson1.html":1726,"tobacco.html":1620,"tusser1.html":1557,"venables1.html":1662,
 "veue1.html":1596,"walton/index.html":1653,"waspes.htm":1615,"wealth/wealth.html":1776,"webster1.html":1623,"webster2.htm":1613,
 "wheatley.html":1773,"wollstonecraft.html":1798,"wollstonecraft2.html":1792,"woolman.html":1774,"arte/arte.htm":1553,"antonie.html":1592,
 "ape.html":1607,"arcadia1.html":1590,"areopagitica.html":1644,"amoretti.html":1595,"astrophel.html":1595,"oberon.htm":1611,
}
# authors who died before 1700 and whose works are all within the window: undated texts
DATELESS_OK = {"foxep.htm", "penington1.html", "sidpsalms.html"}
OVERRIDE_CHILD = {"queene1.html": 1590, "queene2.html": 1590, "queene3.html": 1590}
MIDDLE = {"curial.html", "berners/berners.html", "everyman.html", "spare.html"}
NOTE_RE = re.compile(r"Note\b[^.]{0,30}(e-?text|Web edition|edition|:)|Renascence\s+Editions\s+(text|imprint|etext)|This html etext|prepared from|Transcription\s+by|Transcribed", re.S)

def clean(html):
    s = BeautifulSoup(html, "lxml")
    for t in s(["script", "style", "img", "noscript"]):
        t.decompose()
    for a in s.find_all("a", href=True):
        if a["href"].endswith("ren.htm") or "scholarsbank" in a["href"] or "hdl.handle" in a["href"]:
            a.decompose()
    body = s.body or s
    # drop the leading note block(s) by the publisher (modern), within the first part of the document
    ps = body.find_all(["p", "blockquote", "div", "td"])
    limit = max(1, int(len(ps) * 0.3))
    n = 0
    for p in ps[:limit]:
        t = p.get_text(" ", strip=True)
        if t and len(t) < 1800 and NOTE_RE.search(t) and not p.find(["table"]):
            p.decompose(); n += 1
            if n >= 6:
                break
    txt = body.get_text("\n", strip=True)
    txt = re.sub(r"^(.*?\n)?Return to\s*\n?(?:Renascence\s*\n?Editions\s*\n?)?", lambda m: (m.group(1) or ""), txt, count=1, flags=re.S) if txt[:300].count("Return to") else txt
    head, tail = txt[:2500], txt[2500:]
    head = re.sub(r"\[\s*(?:PDF[^\]]*)?\]", " ", head)
    head = re.sub(r"(?:Note\b[^\n]{0,40}(?:e-?text|Web edition|edition|imprint)|This html etext|Renascence\s+Editions\s+(?:text|imprint)).{0,1600}?(?:uses only\.|use only\.|Dedicated to[^\n]*\n?|rbear@[^\n]*\n?|educational uses\.?)", " ", head, count=1, flags=re.S | re.I)
    txt = head + tail
    txt = re.sub(r"\n(Renascence\s+Editions\s*)+$", "", txt)
    return txt

kids = {}
for k, p in parent_of.items():
    kids.setdefault(p, []).append(k)

def top_ancestor(k):
    while k in parent_of:
        k = parent_of[k]
    return k

n_modern = 0
for k, html in pages.items():
    txt = clean(html)
    words = len(txt.split())
    if k in kids and words < 1000:
        continue  # pure index/frontispiece page of a work divided into parts
    if k.startswith("montaigne/book") and k in kids:
        continue
    anc = top_ancestor(k)
    if k in OVERRIDE_CHILD:
        year = OVERRIDE_CHILD[k]
    else:
        year = YEAR.get(k, YEAR.get(anc)) if k in parent_of or True else None
    dateless = False
    if k in DATELESS_OK:
        year, dateless = None, True
    elif year is None:
        head = txt[:1500]
        yy = [int(x) for x in re.findall(r"(?<!\d)(1[4-7]\d\d)(?!\d)", head[:1500])]
        year = yy[0] if yy else None
        problems.append(f"year taken from page head for {k}: {year}")
    lang = "Middle English" if k in MIDDLE else "English"
    if words < 60 and year is None:
        problems.append(f"{k}: frame/empty page, no text (Sidney's Lady of May frameset)"); continue
    h.add(slug(k) + ".txt", txt, language=lang, year=year, source=f"Renascence Editions: {k}", url=BASE + k, dateless_in_window=dateless)

rep = h.finish(
    method="Read the Luminarium mirror index (ren.htm / root), followed every HTML link to a text (crawl delay 1 s, robots.txt allows all except /cgi-bin), and for works divided into parts/chapters followed the links to the part pages (2 levels for Montaigne). Extracted body text with BeautifulSoup after removing site header/footer, links to the index and the publisher's e-text note. One record per HTML page (a play, poem, tract or a book/part of a longer work). Year = year of the original printing/composition of the work, set from a table made from the page headers (not the date of the e-text or of the source edition).",
    coverage=f"All {len(top)} listed HTML targets of the index and the part pages of divided works were fetched (pages cached in files/). PDF-only items (e.g. Spenser Faerie Queene complete PDF, the Scholars Bank PDFs) were not used as the HTML versions are the same texts. Modern essays by Bear/Renchler, introductions and the reader essay were excluded. Out-of-period works (after 1700) are kept in staging with their years for counting out.",
    problems=problems + [
        "Several texts (Shakespeare plays from the ERIS/Adelaide plain-text edition, Hobbes, Hume, Smith, Fielding, Swift, Paine etc.) are modern editorial texts with normalised spelling; kept since only the spelling is normalised, not the language.",
        "Publisher's e-text notes and editorial comments were removed by heuristic and may remain in some pages; some pages are lightly glossed by the editor (Glossed notes).",
        "Fox Selected Epistles, Penington Some Considerations and Sidney's Psalmes are undated; flagged dateless_in_window because their authors died before 1700 (Fox's epistles are 1650s-1690s, Penington d. 1679, Sidney d. 1586).",
        "Years of composition/publication come from a hand-made table; some (Raleigh, Roper, Spenser View, Sidney psalms) are the date of first printing, not composition.",
    ])
print(rep)
