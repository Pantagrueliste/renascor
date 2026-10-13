import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys,re,html,json
sys.path[:0]=[HARVEST_DIR + ""]
from hlib import Harvest, first_year
from lxml import html as LH
h=Harvest("winthrop-papers-digital-edition")
B="https://www.masshist.org/publications/winthrop/index.php/"
LIMIT=int(sys.argv[1]) if len(sys.argv)>1 else None
probs=[]
br=h.get(B+"browse","files/browse.html")
years=sorted(set(re.findall(r'browse/date\?y=(\d{4})',br)))
ids={}   # id -> browse year
for y in years:
    t=h.get(B+f"browse/date?y={y}",f"files/browse/{y}.html")
    for i in re.findall(r'/view/(PWF\d+d\d+[A-Za-z]*)',t): ids.setdefault(i,int(y))
print(len(years),"years",len(ids),"ids")
def text_of(el):
    for bad in el.xpath('.//a[contains(@class,"note")]|.//note'): bad.getparent().remove(bad) if bad.tail is None else (bad.drop_tree())
    s=el.text_content()
    s=re.sub(r'[ \t\xa0]+',' ',s); s=re.sub(r'\s*\n\s*','\n',s)
    return s.strip()
def lang(raw):
    w=re.findall(r"[a-z]+",raw.lower()); 
    lat=sum(x in ("et","quod","ad","est","cum","sunt","pro","qui","quae","dei","anno","sciatis") for x in w)
    eng=sum(x in ("the","and","of","to","that","is","with","for","this","my","i") for x in w)
    return "Latin" if lat>eng*1.5 and lat>8 else "English"
n=0
for did,y in sorted(ids.items()):
    if LIMIT and n>=LIMIT: break
    n+=1
    try: t=h.get(B+"view/"+did,f"files/doc/{did}.html")
    except Exception as e: probs.append(f"{did}: {e}"); continue
    root=LH.fromstring(t)
    bodies=root.xpath('//*[@type="docbody"]')
    if not bodies: probs.append(f"{did}: no docbody"); continue
    raw="\n\n".join(text_of(b) for b in bodies)
    if not raw.strip(): probs.append(f"{did}: empty body"); continue
    doc=root.xpath('//doc')
    stype=doc[0].get('stype') if doc else None
    h1=root.xpath('//doc/bibl//h3/text()')
    yr=first_year(h1[0]) if h1 else None
    year=yr or y
    h.add(f"{did}.txt",raw,language=lang(raw),year=year,source="Winthrop Papers Digital Edition (MHS)",url=B+"view/"+did,doctype=stype)
print(h.finish(method="Document pages (/view/<id>) enumerated through the browse-by-date pages; only the document body (div2/div3 type=docbody: address, salutation, text, closing) was kept; editorial header, footnote markers and back-matter notes (docback) removed. No bulk export, API or TEI download found; /sitemap.xml is a routing error.",coverage=f"{len(h.records)} of {len(ids)} documents listed in the browse-by-date pages (volumes 1-4 only are online).",problems=probs))
