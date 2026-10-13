import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, io, zipfile, re
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
h = Harvest("folger-shakespeare")
data = h.get("https://flgr.sh/txtfssAllxml", "files/all_xml.zip", binary=True)
# approximate composition dates (scholarly consensus, Folger/Oxford chronology)
Y = {"1H4":1597,"2H4":1598,"1H6":1592,"2H6":1591,"3H6":1591,"Ado":1598,"All":1605,"Ant":1606,"AWW":1605,"AYL":1599,
"Cor":1608,"Cym":1610,"Err":1594,"H5":1599,"H8":1613,"Ham":1601,"JC":1599,"Jn":1596,"LLL":1595,"Lr":1606,"Luc":1594,
"Mac":1606,"MM":1604,"MND":1595,"MV":1597,"Oth":1604,"Per":1608,"PhT":1601,"R2":1595,"R3":1593,"Rom":1595,"Shr":1592,
"Son":1600,"TGV":1592,"Tim":1607,"Tit":1593,"TN":1601,"TNK":1613,"Tmp":1611,"Tro":1602,"Ven":1593,"Wiv":1598,"WT":1610}
outer = zipfile.ZipFile(io.BytesIO(data))
for n in sorted(outer.namelist()):
    if n.startswith("__MACOSX") or not n.endswith(".zip"): continue
    inner = zipfile.ZipFile(io.BytesIO(outer.read(n)))
    xs = [m for m in inner.namelist() if m.endswith(".xml") and not m.startswith("__MACOSX")]
    for m in xs:
        raw = inner.read(m).decode("utf-8")
        code = re.search(r"<idno>([^<]+)</idno>", raw).group(1)
        title = re.search(r"<title>([^<]+)</title>", raw).group(1)
        y = Y.get(code)
        if y is None: print("NO YEAR", code, title)
        h.add(m.split("/")[-1], raw, language="English", year=y, source=f"Folger Shakespeare: {title}",
              url="https://www.folger.edu/explore/shakespeares-works/download/")
rep = h.finish(method="Downloaded the all-plays XML bundle (flgr.sh/txtfssAllxml, nested per-work zips) and took each work's TEI file. Years are approximate composition dates from scholarly chronology (TEI header only has modern edition dates).",
  coverage="All works in the bundle (plays, Sonnets, narrative poems). Modern-spelling Folger editions; the only version offered as XML.",
  problems=["Texts are modern-spelling editions, not diplomatic; no original-spelling version is offered.",
            "year = approximate composition date (c. 1591-1613), not from TEI header; editorial introductions are not in the XML."])
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"])
