import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, zipfile, io, re, html
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year, slug
h = Harvest("hartlib-papers")
url = "https://www.dhi.ac.uk/san/data/hartlib/hartlib-txt.zip"
z = zipfile.ZipFile(io.BytesIO(h.get(url, "files/hartlib-txt.zip", binary=True)))

STOP = {
 "English": set("the and of to that is which with for this his not be are have as by it from".split()),
 "Latin": set("et est in non ad quod cum sed ut quae qui de ex esse sunt per enim etiam".split()),
 "German": set("und der die das ist nicht mit den von zu ein eine auch sich dem dasz wie auf".split()),
 "French": set("et le la les de des que est pour dans un une qui par sur ne pas en du".split()),
 "Dutch": set("en de het van een dat niet met voor zijn op aan ook als".split()),
}
def lang(t):
    w = re.findall(r"[a-zA-Z]+", t.lower())
    sc = {k: sum(x in s for x in w) for k, s in STOP.items()}
    best = max(sc, key=sc.get)
    return best if sc[best] >= 3 else "English"

def clean(x):
    m = re.search(r"<TRANSCRIPTION>(.*?)(</TRANSCRIPTION>|$)", x, re.S | re.I)
    body = m.group(1) if m else x
    body = re.sub(r"<(EDITOR|REND|IMAGE)\b[^>]*>.*?</\1>", " ", body, flags=re.S | re.I)
    body = re.sub(r"<(TAB|SP)\s*/?>", " ", body, flags=re.I)
    body = re.sub(r"</BLOCK>", "\n", body, flags=re.I)
    body = re.sub(r"<[^>]+>", "", body)
    body = html.unescape(body)
    return re.sub(r"[ \t]+", " ", body).strip()

noyear = 0
for n in sorted(z.namelist()):
    if not n.endswith(".txt") or n.startswith("__MACOSX") or "/." in n:
        continue
    cat = n.split("/")[1]
    x = z.read(n).decode("utf-8", "replace")
    d = re.search(r"<DATING>(.*?)</DATING>", x, re.S | re.I)
    t = re.search(r"<TITLE>(.*?)</TITLE>", x, re.S | re.I)
    year = first_year(d.group(1)) if d else None
    raw = clean(x)
    noyear += year is None
    h.add(f"{cat}/{n.split('/')[-1]}", raw, language=lang(raw), year=year,
          source="Hartlib Papers", url="https://www.dhi.ac.uk/hartlib/",
          title=html.unescape(re.sub(r"<[^>]+>", "", t.group(1))) if t else "",
          dating=d.group(1) if d else "")
rep = h.finish(
    method="DHI Data Service zip hartlib-txt.zip (found via data service API /api/data/project?project=hartlib); the file-level headers parsed; only <TRANSCRIPTION> kept as plain text, editorial <EDITOR>/<REND>/<IMAGE> markers removed, entities unescaped; year = first year of <DATING>; language by stopword heuristic.",
    coverage="All 5,740 text files (main 5,234, additional 442, pamphlets 64) of hartlib-txt.zip. The cleaned/lemmatised Turing version and page images were not downloaded.",
    problems=[f"{noyear} files have no usable year in DATING (UNDATED etc.): year=None, dateless_in_window=False, so not counted in window.",
              "The /hartlib/ site sits behind a proof-of-work browser check; the data service download (no gate) was used instead.",
              "Language is assigned per file by a stopword heuristic (English default); Latin/German/French items may be misassigned. 'additional' includes some later printed editions of Hartlib letters (e.g. Boyle's Works, 1772) whose transcribed letter text is dated by the letter."])
print(rep)
