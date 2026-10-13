import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys,re,html
sys.path[:0]=[HARVEST_DIR + ""]
from hlib import Harvest
h=Harvest("erdy-kodex")
B="https://sermones.elte.hu/erdy/"
idx=h.get(B,"files/index.html")
pages=list(dict.fromkeys(re.findall(r'href="html/(\d+\.html)"',idx)))
probs=[];out=[]
def clean(s):
    s=re.sub(r'<a [^>]*name="_ftnref\d+"[^>]*>.*?</a>','',s,flags=re.S)
    s=re.sub(r'<br\s*/?>|</p>','\n',s,flags=re.I)
    s=re.sub(r'<[^>]+>','',s); s=html.unescape(s)
    s=re.sub(r'[ \t]+',' ',s); s=re.sub(r'\s*\n\s*','\n',s)
    return s.strip()
for p in pages:
    try: t=h.get(B+"html/"+p,"files/"+p)
    except Exception as e: probs.append(f"{p}: {e}"); continue
    body=t.split('<div id="footer">')[0]
    rows=re.findall(r'<tr>(.*?)</tr>',body,flags=re.S)
    L=[];R=[]
    for r in rows:
        tds=re.findall(r'<td[^>]*>(.*?)</td>',r,flags=re.S)
        if len(tds)<3 or '<h2>' in r: continue
        L.append(clean(tds[1])); R.append(clean(tds[2]))
    out.append("\n".join(x for x in L+R if x))
raw="\n".join(out)
print(len(pages),len(out),len(raw.split()))
h.add("erdy-kodex.txt",raw,language="Hungarian",year=1527,source="Érdy-kódex (Sermones Compilati, ELTE): diplomatic transcription",url=B)
print(h.finish(method="Per-spread HTML pages (html/NNN.html) listed in the index table; line-number column, footnote markers and footnotes (editorial notes, in Hungarian) removed; left then right page column joined.",coverage=f"Transcribed pages available online only: {len(out)} page files covering pages 001-055 and 103-157; the rest of the critical edition is 'in preparation'.",problems=probs+["Dated 1526-1527 (copied); year 1527 used. Transcription uses ASCII markup for special letters (e.g. /y:/, /o'/), left as is."]))
