import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys,re,html
sys.path[:0]=[HARVEST_DIR + ""]
from hlib import Harvest
import subprocess,time
h=Harvest("weinsberg-gedenkbuecher")
class R:
    def __init__(s,code,data): s.status_code=code; s.content=data; s.encoding="iso-8859-1"; s.apparent_encoding="iso-8859-1"
    @property
    def text(s): return s.content.decode("iso-8859-1")
    def raise_for_status(s):
        if s.status_code>=400:
            import requests; e=requests.HTTPError(f"HTTP {s.status_code}"); e.response=s; raise e
class S:
    headers={}
    def get(self,url,timeout=60,**kw):
        # Python's bundled LibreSSL fails the TLS handshake with this host; use curl (follows the case-changing redirect)
        o=subprocess.run(["curl","-sL","-m","60","-A",h.s.headers["User-Agent"],"-w","\n%{http_code}",url],capture_output=True)
        body,_,code=o.stdout.rpartition(b"\n")
        return R(int(code or 0),body)
h.s=S(); h.s.headers={"User-Agent":"Renascor-harvest/0.1 (+https://pantagrueliste.github.io/renascor/)"}
import requests
B="https://www.weinsberg.uni-bonn.de/Edition/"
books=[("Liber_Iuventutis","li",8,"Liber Iuventutis"),("Liber_Senectutis","ls",11,"Liber Senectutis"),("Liber_Decrepitudinis","ld",10,"Liber Decrepitudinis")]
probs=[]
def clean(t):
    t=re.sub(r'<a href="marg[^"]*"[^>]*>.*?</a>','',t,flags=re.S)       # page/margin reference links
    t=re.sub(r'<a href="[^"]*Titelblatt[^"]*"[^>]*>.*?</a>','',t,flags=re.S)
    t=t.split('<body',1)[-1]
    t=re.sub(r'<(script|style)\b.*?</\1>','',t,flags=re.S|re.I)
    t=re.sub(r'</div>|<br\s*/?>','\n',t,flags=re.I)
    t=re.sub(r'<[^>]+>','',t); t=html.unescape(t)
    t=re.sub(r'[ \t\xa0]+',' ',t); t=re.sub(r'\s*\n\s*','\n',t)
    return t.strip()
for d,pre,nmax,title in books:
    parts=[];n=0
    for i in range(1,nmax+6):
        try: t=h.get(f"{B}{d}/{pre}{i}.htm",f"files/{d}/{pre}{i}.htm")
        except requests.HTTPError as e:
            if e.response.status_code==404 and i>nmax: break
            probs.append(f"{d}/{pre}{i}: {e}"); continue
        parts.append(clean(t)); n+=1
    raw="\n".join(parts)
    print(d,n,len(raw.split()))
    h.add(f"{d}.txt",raw,language="German",year=None,dateless_in_window=True,source=f"Weinsberg, {title}",url=f"{B}{d}/{d}.htm")
    h.records[-1]["note"]="Cologne German with Latin passages; book covers 1518-1597 (Iuventutis from 1518)."
print(h.finish(method="Per-book HTML text pages (liN/lsN/ldN.htm, the 'Text' frame of each frameset), concatenated per book; reference links, markup and navigation removed. Marginal notes (marg*.htm), indexes and introductions not included.",coverage="All three books (files li1-8, ls1-11, ld1-10) as listed on the frameset pages.",problems=probs+["Per-book year is not in the markup: set year=None with dateless_in_window=True because the whole work dates from 1518-1597 (per catalogue). Main language German with Latin passages and grey-font editorial reconstructions of damaged text left in. Marginal notes (author's original marginalia) were not harvested."]))
