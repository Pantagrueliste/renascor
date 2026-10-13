import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, io, re, tarfile
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
from lxml import etree
h = Harvest("bodley-diplomatic-correspondence")
tb = h.get("https://codeload.github.com/livesandletters/bodley1/tar.gz/master", "files/bodley1-master.tar.gz", binary=True)
tf = tarfile.open(fileobj=io.BytesIO(tb))
SKIP_SECTIONS = {"editorial", "endorsement", "lateraddition"}
SKIP_TAGS = {"folioref", "catchword", "image", "drawing"}

def render(el, out):
    tag = el.tag
    if not isinstance(tag, str):
        return
    if tag in SKIP_TAGS:
        return
    if tag == "section" and el.get("Section") in SKIP_SECTIONS:
        return
    if tag == "newline":
        out.append("\x00NL")
        return
    if el.get("replace") is not None and tag in ("super", "overline", "scharfes_s", "abbreviation", "digraph", "underline", "linethrough", "insert_symbol"):
        out.append(el.get("replace"))
        return
    if el.text:
        out.append(el.text.replace("\n", "").replace("\r", ""))
    for c in el:
        render(c, out)
        if c.tail:
            out.append(c.tail.replace("\n", "").replace("\r", ""))

def to_text(root):
    out = []
    for lt in root.iter("lettertext"):
        render(lt, out)
        out.append("\x00NL")
    # also address leaves outside lettertext (superscription kept)
    s = ""
    for p in out:
        if p == "\x00NL":
            if s.endswith("-"):
                s = s[:-1]
            else:
                s += " "
        else:
            s += p
    return re.sub(r"[ \t]+", " ", s).strip()

n_empty = 0
mism = 0
empties = []
for m in sorted(tf.getmembers(), key=lambda m: m.name):
    mm = re.fullmatch(r"[^/]+/xml/(\d{4})/([^/]+\.xml)", m.name)
    if not mm:
        continue
    data = tf.extractfile(m).read()
    root = etree.fromstring(data, etree.XMLParser(recover=True, huge_tree=True))
    txt = to_text(root)
    if len(txt.split()) < 3:
        empties.append(mm.group(2)); continue
    # endorsement date as sanity check
    h.add(f"{mm.group(1)}/{mm.group(2)}", txt, language="English", year=int(mm.group(1)),
          source="Diplomatic Correspondence of Thomas Bodley", url="https://github.com/livesandletters/bodley1/blob/master/xml/" + mm.group(1) + "/" + mm.group(2))
print(h.finish(method="GitHub tarball (codeload) of livesandletters/bodley1 master; xml/<year>/*.xml (project-specific, non-TEI markup). Converted to plain text: contractions shown in the source as <super>/<overline>/<abbreviation>/<scharfes_s> with replace= were expanded using the replace value (as the edition's 'expanded' view); folio refs, catchwords, editorial notes, endorsements/docket notes and later additions removed; line-end hyphenation rejoined; deleted words (<deletion>) kept.",
  coverage=f"All {len(h.records)} letter files with transcribed letter text of the 988 XML files in the repository (1585-1597); {len(empties)} files with no letter text (address leaf only or empty) skipped: {', '.join(empties)}.",
  problems=["Year taken from the repository's year directory (1585-1597), not parsed from each letter's date; a few letters may be misfiled by a year.", "Project markup is not TEI; text reconstruction is heuristic (whitespace in the XML is formatting only).", "Letters are by Bodley and correspondents; some contain foreign-language phrases, counted as English.", "The 990 in the catalogue vs 988 XML files in the repo (the repo has year folders 1585-1597)."]))
