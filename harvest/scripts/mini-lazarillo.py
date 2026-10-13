import os as _os; HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
sys.path.insert(0, HARVEST_DIR)
from hlib import Harvest, tei_year, first_year, slug
import tarfile, io, re
from lxml import etree

NS = {"t": "http://www.tei-c.org/ns/1.0"}
T = "{http://www.tei-c.org/ns/1.0}"
h = Harvest("mini-lazarillo")
problems = []
data = h.get("https://codeload.github.com/minilazarillo/minilazarillo.github.io/tar.gz/master", "files/ml.tar.gz", binary=True)
tf = tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")
member = [m for m in tf.getmembers() if m.name.endswith("/xml/lazarillo-master.xml")][0]
xml = tf.extractfile(member).read()
root = etree.fromstring(xml)
year = tei_year(xml.decode("utf-8-sig"))  # 1554 from sourceDesc

def render(el):
    out = []
    def walk(e):
        tag = etree.QName(e).localname if isinstance(e.tag, str) else None
        if tag is None:  # comment / PI
            return
        if tag in ("note", "reg", "corr"):  # editorial apparatus: keep the printed (orig/sic) reading only
            return
        if tag == "pb":
            pass
        out.append(e.text or "")
        for c in e:
            walk(c)
            out.append(c.tail or "")
        if tag in ("p", "ab", "head", "l"):
            out.append("\n")
    walk(el)
    return re.sub(r"[ \t\r\n]+", " ", "".join(out).replace("\n", "\n")) 

body = root.find(".//t:body", NS)
for div in body.findall("t:div", NS):
    did = div.get("{http://www.w3.org/XML/1998/namespace}id")
    paras = []
    for e in div.iter(T + "p", T + "ab", T + "head"):
        txt = re.sub(r"\s+", " ", render(e)).strip()
        if txt:
            paras.append(txt)
    raw = "\n".join(paras)
    h.add(f"{did}.txt", raw, language="Spanish", year=year, source=f"La vida de Lazarillo de Tormes (Medina del Campo, 1554), {did}, Mini Lazarillo TEI master",
          url="https://github.com/minilazarillo/minilazarillo.github.io/blob/master/xml/lazarillo-master.xml")
problems.append("Text is the editors' modernised-spelling reading of the 1554 Medina del Campo print (accepted). Where the TEI encodes <choice><orig>/<reg> pairs the original (orig) reading was kept, the regularised form dropped; the other silent modernisations (accents, i/y, v/b) cannot be recovered. <sic> readings kept.")
problems.append("Back matter (list of persons, places with commentary notes) excluded; page-break markers dropped. Prologue and seven tratados are separate records; the colophon is inside tratado 7.")
rep = h.finish(method="Downloaded the GitHub repository tarball once (codeload) and parsed xml/lazarillo-master.xml with lxml; one record per top-level <div> of the body (prologue and tratados 1-7), plain text with notes and apparatus removed.",
    coverage="All of the TEI master text (prologue, 7 tratados, colophon). The annotated HTML edition and facsimile images were not used.",
    problems=problems)
print(rep)
