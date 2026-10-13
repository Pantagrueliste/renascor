import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, json
HD = HARVEST_DIR + ""
sys.path.insert(0, HD)
from hlib import Harvest, slug
from lxml import etree
RID = "philipp-hainhofer-reiseberichte-sammlungsbeschreibungen-1594-1636-annotated-digital-edition"
h = Harvest(RID)
problems = []
meta = json.loads(h.get("https://heidata.uni-heidelberg.de/api/datasets/:persistentId/?persistentId=doi:10.11588/DATA/DVU14P", "files/dataset.json"))
files = meta["data"]["latestVersion"]["files"]
NS = "{http://www.tei-c.org/ns/1.0}"
for f in files:
    lab = f["label"]
    if not lab.endswith(".xml") or lab.startswith("hainhofer-lod"):
        continue
    fid = f["dataFile"]["id"]
    data = h.get(f"https://heidata.uni-heidelberg.de/api/access/datafile/{fid}", "files/" + slug(lab), binary=True)
    root = etree.fromstring(data)
    for el in list(root.iter(NS + "note")):
        if el.get("resp") == "#editor" or el.get("type") == "annotation":
            # drop editorial annotations (keep tail)
            p = el.getparent(); t = el.tail
            prev = el.getprevious()
            if t:
                if prev is not None: prev.tail = (prev.tail or "") + t
                else: p.text = (p.text or "") + t
            p.remove(el)
    for el in list(root.iter(NS + "expan")):  # keep original abbreviation, not the expansion
        p = el.getparent(); t = el.tail; prev = el.getprevious()
        if t:
            if prev is not None: prev.tail = (prev.tail or "") + t
            else: p.text = (p.text or "") + t
        p.remove(el)
    body = root.find(f".//{NS}text")
    raw = etree.tostring(body, encoding="unicode")
    m = re.search(r"(1[5-6]\d\d)", lab)
    year = int(m.group(1)) if m else None
    if year is None: problems.append(f"no year in {lab}")
    h.add(lab, raw, language="German", year=year, source="Hainhofer: " + lab[:-4], url="https://doi.org/10.11588/DATA/DVU14P")
rep = h.finish(method="heiDATA dataset doi:10.11588/DATA/DVU14P (TEI/XML per journey, CC BY-SA 4.0); editorial note[type=annotation] (gloss, translation, commentary) and <expan> removed; year = journey year from filename",
    coverage="All TEI journey/collection-description files in the published dataset (one text per journey); further phases of the project are not yet published. hainhofer-lod.xml and registers excluded.",
    problems=problems + ["Text dated by the journey year in the file name; Hainhofer's Reiseberichte were written c. same year."])
print(json.dumps(rep, ensure_ascii=False)[:600])
