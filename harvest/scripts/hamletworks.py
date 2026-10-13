import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys,re,html
sys.path[:0]=[HARVEST_DIR + ""]
from hlib import Harvest
h=Harvest("hamletworks")
H="https://server-66-113-234-189.da.direct/global-language.com/html/ENFOLDED/enhamp.php?frametype=frames&type="
def deent(c):
    c=re.sub(r'<[^>]+>','',c); c=html.unescape(c).replace('\xa0',' ')
    return re.sub(r'[ \t]+',' ',c).strip()
q=h.get(H+"Q2","files/Q2.html")
t=re.sub(r'<!--.*?-->','',q,flags=re.S)
out=[]
for r in re.findall(r'<tr>(.*?)</tr>',t,flags=re.S):
    tds=re.findall(r'<td[^>]*>(.*?)</td>',r,flags=re.S)
    if not tds: continue
    c=re.sub(r'<a [^>]*>.*?</a>','',tds[0],count=1,flags=re.S)     # line number link
    c=deent(c)
    if c: out.append(c)
h.add("hamlet-Q2.txt","\n".join(out),language="English",year=1604,source="Hamletworks: Enfolded Hamlet, Second Quarto text (1604/5)",url=H+"Q2")
f=h.get(H+"F1","files/F1.html")
f=re.sub(r'<!--.*?-->','',f,flags=re.S)
body=f.split('</form>',1)[-1]
lines=[]
for m in re.finditer(r'<l>(.*?)</l>',body,flags=re.S):
    c=re.sub(r'<a [^>]*>.*?</a>','',m.group(1),count=1,flags=re.S)
    c=re.sub(r'<i>\s*\d+\.\d+\.\d+\s*</i>','',c)          # modern act.scene.line references
    c=deent(c)
    if c: lines.append(c)
h.add("hamlet-F1.txt","\n".join(lines),language="English",year=1623,source="Hamletworks: Enfolded Hamlet, First Folio text (1623)",url=H+"F1")
print(h.finish(method="Full-text 'Q2' and 'F1' views of the Enfolded Hamlet (enhamp.php?type=Q2 / F1) on the redirected host server-66-113-234-189.da.direct; line numbers, hidden HTML comments (cross-version line references) and modern scene references removed. The 'Q2 Only'/'F1 Only' views (variant readings), the modern enfolded text, commentary, textual notes and the DjVu/PDF Q1 and Q6 files not used.",coverage="Q2 and F1 texts of Hamlet in full (2 texts). Q1 (1603) and Q6 diplomatic versions exist only as PDF/DjVu images and were not harvested.",problems=["F1 view has irregular markup (unclosed <i>/<l>); page signatures and a few act/scene headings may be mixed in. Server hamletworks.org redirects to server-66-113-234-189.da.direct (no robots.txt there). Q1 1603 out of scope (PDF scans)."]))
