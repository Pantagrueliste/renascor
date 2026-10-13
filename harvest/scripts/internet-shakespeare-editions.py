import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys,re,html,json
sys.path[:0]=[HARVEST_DIR + ""]
from hlib import Harvest, first_year
import requests
from lxml import html as LH
h=Harvest("internet-shakespeare-editions")
B="https://internetshakespeare.uvic.ca/"
probs=[]
idx=h.get(B+"Foyer/Texts/index.html","files/texts_index.html")
paths=sorted(set(re.findall(r'href="\.\./\.\./((?:Annex|Library)/Texts/[^"]+)"',idx)))
codes={}
for p in paths:
    m=re.search(r'Texts/([^/.]+)',p); codes[m.group(1)]=p
codes.setdefault("Oth","Library/Texts/Oth/index.html")   # not in the index page but exists
docs={}   # id -> label
for code,p in sorted(codes.items()):
    tried=[p]+[q for q in (f"Annex/Texts/{code}/index.html",f"Library/Texts/{code}/index.html",f"Library/Texts/{code}.html") if q!=p]
    page=None
    for q in tried:
        try: page=h.get(B+q,f"files/play/{code}.html"); break
        except requests.HTTPError: continue
    if page is None: probs.append(f"{code}: play page not found"); continue
    for m in re.finditer(r'<a [^>]*href="[^"]*doc/([^/"]+)/index\.html"[^>]*>(.*?)</a>',page,flags=re.S):
        i,lab=m.group(1),re.sub(r'\s+',' ',re.sub('<[^>]+>','',m.group(2))).strip()
        suffix=i.split("_",1)[-1]
        if "Old-spelling" in lab or (i.startswith(code+"_") and re.fullmatch(r'(Q\d*[ab]?|F\d?|O\d)',suffix)):
            docs.setdefault(i,lab)
print(len(docs),sorted(docs))
def year_of(root,did):
    t=root.xpath('//title/text()')
    title=t[0] if t else ""
    y=first_year(title)
    return y,title
for did in sorted(docs):
    try: t=h.get(B+f"doc/{did}/complete/index.html",f"files/doc/{did}.html")
    except Exception as e: probs.append(f"{did}: {e}"); continue
    root=LH.fromstring(t)
    ls=root.xpath('//div[@class="innerContent"]//div[contains(concat(" ",@class," ")," line ")]')
    out=[]
    for l in ls:
        for a in l.xpath('.//a[contains(@class,"milestone")]'): a.drop_tree()
        s=re.sub(r'\s+',' ',l.text_content()).strip()
        if s: out.append(s)
    if not out: probs.append(f"{did}: no text lines"); continue
    y,title=year_of(root,did)
    title=re.sub(r'\s*::.*','',title).strip()
    if y is None and did=="Per_Q1": y=1609; probs.append("Per_Q1: title has no year; set to 1609 (Pericles Q1, known imprint date)")
    elif y is None: probs.append(f"{did}: no year in title '{title}'")
    h.add(f"{did}.txt","\n".join(out),language="English",year=y,source=f"Internet Shakespeare Editions: {title}",url=B+f"doc/{did}/",title=title)
print(h.finish(method="Per-witness old-spelling transcriptions found via the play index pages (Foyer/Texts/index.html -> play page -> 'Old-spelling transcription' links); the 'complete' view (doc/<id>/complete/index.html) was parsed for div.line elements, dropping through-line-number milestones. Modern-spelling editions (_M), introductions, notes, apparatus and facsimiles not used. No XML/bulk export found; /sitemap.xml is 404; /exist/ is disallowed by robots.txt and not touched.",coverage=f"{len(h.records)} old-spelling witnesses (quartos/folio) of {len(codes)} plays and poems listed on the Texts index.",problems=probs))
