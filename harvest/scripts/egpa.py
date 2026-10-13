import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, html, urllib.parse
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year, slug
h = Harvest("egpa")
B = "https://corpora.uah.es/egpa/"
ids = set()
for q in ["", "&folder=xmlfiles/EGPAdoc", "&folder=xmlfiles/EGPAlit", "&folder=xmlfiles/7PartidasDigital"]:
    pg = h.get(B + "index.php?action=files" + q, f"files/list_{slug(q) or 'root'}.html")
    ids |= {x.replace("&amp;", "&") for x in re.findall(r"action=file&(?:amp;)?(?:id|cid)=([^'\"&<>]+)", pg)}
skip = re.compile(r"prueba|proba|prova|Curso|z_", re.I)
problems = []; skipped = []; hashes = {}
def fy(s):
    m = re.search(r"(?<!\d)(1[0-9]\d\d)(?!\d)", s or "")
    return int(m.group(1)) if m else None
def dateof(x):
    for pat in (r"<origDate\b[^>]*\b(?:when|notBefore|from)=\"([^\"]+)\"", r"<origDate\b[^>]*>(.*?)</origDate>", r"<date\b[^>]*\bwhen=\"([^\"]+)\"[^>]*>"):
        for m in re.finditer(pat, x[:20000], re.S):
            y = fy(m.group(1))
            if y: return y, m.group(0)[:80]
    return None, None
for i in sorted(ids):
    if skip.search(i.split("/")[-1]): skipped.append(i); continue
    try: x = h.get(B + "xmlfiles/" + i.replace("+", "%20"), "files/xml/" + slug(urllib.parse.unquote_plus(i)))
    except Exception as e: problems.append(f"{i}: {e}"); continue
    if "<text" not in x: skipped.append(i); continue
    y, _ = dateof(x)
    if y is None:
        m = re.search(r"<sourceDesc.*?</sourceDesc>", x, re.S)
        y = fy(m.group(0)) if m else None
    if y is None:
        tm = re.search(r"<title>(.*?)</title>", x, re.S)
        y = fy(tm.group(1)) if tm else None
    body = re.sub(r"<[^>]+>", " ", x[x.find("<text"):])
    if len(body.split()) < 3 or "work in progress" in body: skipped.append(i + " (placeholder)"); continue
    import hashlib
    hs = hashlib.md5(x.encode()).hexdigest()
    if hs in hashes: skipped.append(i + " (duplicate of " + hashes[hs] + ")"); continue
    hashes[hs] = i
    h.add(slug(urllib.parse.unquote_plus(i)), x, language=("Spanish" if i.startswith("CARTERAS") else "Galician-Portuguese"), year=y, source="EGPA", url=B + "xmlfiles/" + i)
und = [r["filename"] for r in h.records if r["year"] is None]
if skipped: problems.append(f"{len(skipped)} files skipped (test/trial/course files or no <text>): {skipped[:12]}")
if und: problems.append(f"{len(und)} texts without a date in the header (year=None, not counted): {und[:15]}")
problems.append("Texts labelled Galician-Portuguese except CARTERAS_* (Spanish); a few other documents may be Castilian or Latin. Raw is the TEITOK tokenised TEI (tok/note markup incl. editorial footnotes inside <note>; RQ counter keeps <text>). Most texts are medieval and fall outside 1450-1700.")
print(h.finish(method="TEITOK file lists (index.php?action=files, root + folders) -> every TEI file fetched from corpora.uah.es/egpa/xmlfiles/; year from origDate in msDesc (fallback: year in <title>).",
  coverage=f"{len(h.records)} TEI files of {len(ids)} listed (rest are test files); full platform content at harvest date.", problems=problems))
