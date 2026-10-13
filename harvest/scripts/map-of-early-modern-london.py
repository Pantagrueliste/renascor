import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys; sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
from lxml import etree
import re, collections, json
h = Harvest("map-of-early-modern-london")
base = "https://mapoflondon.uvic.ca/xml/original/"
idx = h.get(base, "files/original_index.html")
rows = re.findall(r'<a href="([^"?/][^"]*)\.xml">[^<]*</a></td><td align="right">[^<]*</td><td align="right">([^<]*)<', idx)
def kb(x):
    x = x.strip()
    return float(x[:-1]) * (1 if x[-1] == "K" else 1024) if x[-1] in "KM" else float(x) / 1024
size = {n: kb(x) for n, x in rows}
txt_ids = "CARR1,WILL10,SHIP2,EPIC1,EIRE1,CHRY1,STAP1,SABB2,BURI1,PETI1,MARR1,SIRT1,GREA5,TRIU1,MORT8,MAGN3,AMWE1,WEST14,TESI1,DIXI2,COLD2,CHRU1,QMPS1,LOVE8,TRIU2,METR1,SIDE1,ORDE1,ASST1,HIMA1,PLAG2,TROI1,LOTT1,CAMP3,OGIL5,PRAI1,IYKN2,SHOE2,REME2,VAGR1,PAEA1,NINE2,SNOW1,DOLE2,EAST3,NEYB1,CLEA1,BART2,OATH1,TALL2,SEVE1,CHEA4,ARCH9,DEVI1".split(",")
cand = [n for n in size if re.fullmatch(r"[A-Z]+\d+", n) and (size[n] >= 15 or n in txt_ids)]
cand += [n for n in size if n.startswith("stow_") and not n.endswith(("progress_chart", "_full", "_TOC"))]
cand = list(dict.fromkeys(cand))
print(len(cand), "candidates", flush=True)
T = "{http://www.tei-c.org/ns/1.0}"
docs = {}
fails = []
for n in cand:
    try:
        docs[n] = h.get(base + n + ".xml", f"files/original/{n}.xml")
    except Exception as e:
        fails.append(f"{n}: {e}")
print("fetched", len(docs), "fails", len(fails), flush=True)
def cats(raw):
    head = raw[: raw.find("</profileDesc>")] if "</profileDesc>" in raw else raw[:30000]
    return re.findall(r'target="mdt:(mdt[A-Za-z]+)"', head)
prim = {}
cc = collections.Counter()
for n, raw in docs.items():
    c = cats(raw)
    isprim = any(x.startswith("mdtPrimarySource") for x in c)
    cc[(isprim, tuple(x for x in c if x.startswith("mdtPrimarySource")))] += 1
    if isprim: prim[n] = (raw, c)
for k, v in cc.most_common(): print(v, k)

def splice(el):
    par = el.getparent(); tail = el.tail or ""
    prev = el.getprevious()
    if prev is not None: prev.tail = (prev.tail or "") + tail
    else: par.text = (par.text or "") + tail
    par.remove(el)
probs = []
for n, (raw, c) in sorted(prim.items()):
    root = etree.fromstring(raw.encode("utf-8"), parser=etree.XMLParser(recover=True, huge_tree=True))
    body = root.find(f"{T}text/{T}body")
    if body is None:
        probs.append(f"{n}: no text/body"); continue
    # original spelling only; modern correction/regularisation dropped
    for tag in ("corr", "reg", "expan"):
        for e in list(body.iter(T + tag)): splice(e)
    # place-name refs and original marginal labels are period text: keep, but rename so they are not dropped as apparatus
    for tag in ("ref", "label"):
        for e in body.iter(T + tag): e.tag = T + "seg"
    title = " ".join("".join(root.find(f"{T}teiHeader/{T}fileDesc/{T}titleStmt/{T}title").itertext()).split())
    m = re.match(r"stow_(1598|1603|1618|1633)_", n)
    if m:
        y = int(m.group(1))
    else:
        sd = root.find(f"{T}teiHeader/{T}fileDesc/{T}sourceDesc")
        y = first_year(" ".join(sd.itertext())) if sd is not None else None
        if y and y > 1750:
            probs.append(f"{n}: sourceDesc year {y} is modern, ignored")
            y = None
        if y is None:
            for d in root.iter(T + "date"):
                v = d.get("when-custom") or d.get("when")
                if v and first_year(v) and first_year(v) <= 1750:
                    y = first_year(v); break
        if y is None:
            mt = re.search(r"(?<!\d)(1[4-6]\d\d)(?!\d)", " ".join(body.itertext()))
            y = int(mt.group(1)) if mt else None
            probs.append(f"{n}: year taken from first year mentioned in the text" if y else f"{n}: no year found")
    kind = "Stow's Survey of London" if n.startswith("stow_") else "Library"
    h.add(f"{n}.xml", "<text>" + etree.tostring(body, encoding="unicode") + "</text>", language="English", year=y,
          source=f"Map of Early Modern London ({kind}): {title}", url=base + n + ".xml", title=title, categories=[x for x in c if x.startswith("mdtPrimarySource")])
probs.append("Selection: documents tagged mdtPrimarySource* (Stow's Survey 1598/1633 sections, mayoral shows, library of royal entries, dramatic extracts, proclamations, broadsides, other texts); gazetteer, personography, bibliography and born-digital encyclopedia entries (modern prose) excluded. Only files >=15 KB in /xml/original/ (plus all stow_* sections) were fetched and tested: a 50-file random sample of the 7-15 KB files contained no primary sources, so a few very small primary texts may be missed.")
probs.append("Stow's Survey is split into section files; the concatenated stow_1598_full (3.7 MB) was not used, to avoid double counting. Front matter, running heads (fw), editorial notes, <corr>/<reg> readings removed; <sic> original readings kept. stow_1603 and stow_1618 are only chapter listings in the release (no text files).")
print(h.finish(method="Directory index of /xml/original/ (no bulk file exists) -> TEI of candidate files fetched one by one; filtered on <catRef target=mdt:mdtPrimarySource*>; body only, <ref>/<label> renamed so the place names and marginalia are counted.",
 coverage="All primary-source documents found among the fetched files; see problems for the selection rule", problems=probs))
