import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, shutil, tarfile, io
import xml.etree.ElementTree as ET
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
RID = "digital-scholarly-edition-of-angelo-poliziano-s-marginal-notes-to-the-epistle-of-sappho-to-phaon"
h = Harvest(RID)
R = "AndreaLaVeglia/Postille_Poliziano_Sappho_EVT"
# one codeload tarball (the repo is ~110 MB because of images); only the XML is extracted
tgz = h.get(f"https://codeload.github.com/{R}/tar.gz/HEAD", "files/repo.tgz", binary=True)
member = "DigitalEditionEVT/data/text/AnnotationesPolitianiInSappho.xml"
xml = None
with tarfile.open(fileobj=io.BytesIO(tgz), mode="r:gz") as tf:
    for m in tf:
        if m.name.endswith(member):
            xml = tf.extractfile(m).read().decode("utf-8"); break
(h.dir / "files" / "AnnotationesPolitianiInSappho.xml").write_text(xml, encoding="utf-8")
(h.dir / "files" / "repo.tgz").unlink()  # keep only the text file, not the 110 MB image archive
NS = "{http://www.tei-c.org/ns/1.0}"
root = ET.fromstring(xml.encode("utf-8"))
ed = next(t for t in root.iter(NS + "text") if t.get("{http://www.w3.org/XML/1998/namespace}id") == "edizione_multilivello")
DROP = {"head", "note", "pb", "del", "bibl", "biblStruct"}
def txt(el):
    tag = el.tag.replace(NS, "")
    if tag in DROP: return el.tail or ""
    if tag == "lb": return "\n" + (el.tail or "")
    if tag == "choice":
        pick = None
        for pref in ("orig", "sic", "abbr"):
            pick = el.find(NS + pref)
            if pick is not None: break
        if pick is None: pick = el[0] if len(el) else None
        return (inner(pick) if pick is not None else "") + (el.tail or "")
    return inner(el) + ("\n" if tag in ("div", "p") else "") + (el.tail or "")
def inner(el):
    s = el.text or ""
    for c in el: s += txt(c)
    return s
t = "\n".join(txt(d) for d in ed.find(NS + "body").iter(NS + "div") if d.get("type") == "postilla")
t = re.sub(r"[ \t]+", " ", t)
t = re.sub(r"\s*\n\s*", "\n", t).strip()
y = first_year(re.search(r"<creation>\s*<date>([^<]+)", xml).group(1))
h.add("AnnotationesPolitianiInSappho.txt", t, language="Latin", year=y, source="Poliziano's marginal notes to the Epistle of Sappho (Bodleian Auct. P 2.2)", url="https://github.com/" + R)
rep = h.finish(method="GitHub codeload tarball of the repository; extracted the TEI file and rebuilt the text of <text xml:id=edizione_multilivello> as plain text (orig/sic/abbr readings kept, deletions, heads, notes and bibliography dropped)",
    coverage="all: the single TEI edition of Poliziano's 238 marginal notes (one record for the whole edition); only the 'postilla' divs of the body are kept; front matter (modern introduction), back matter (loci paralleli), the printed-Ovid 'typis' divs and the second <text> (ipertesto_fonti) excluded",
    problems=["Year 1477 = start of the <creation> date range 1477-1481 for the annotations (copy printed Parma 1477).",
              "Notes quote ancient Latin and Greek authors (Ovid, Strabo...) because Poliziano copied them in the margins; language given as Latin (mixed with Greek).",
              "Licence on the TEI: CC BY-NC-SA 4.0."])
print({k: rep[k] for k in ("texts_total","texts_in_window","words_in_window")})
