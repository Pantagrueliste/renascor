import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import glob,re,json,collections
works=[]
for f in sorted(glob.glob(str(__import__("hlib").OUT) + "/textgrid-repository/lists/works_*.xml")):
    x=open(f,encoding="utf-8").read()
    for r in re.findall(r"<tgs:result.*?</tgs:result>",x,re.S):
        uri=re.search(r"<textgridUri[^>]*>([^<]+)<",r).group(1)
        t=re.search(r"<title>(.*?)</title>",r,re.S).group(1)
        a=re.search(r'<agent role="author"[^>]*>([^<]*)<',r)
        d=re.search(r"<dateOfCreation([^>]*)>([^<]*)<",r)
        works.append((uri,t,a.group(1) if a else "",d.group(1) if d else None,d.group(2) if d else None))
print(len(works))
nod=sum(1 for w in works if w[3] is None); print("nodate",nod)
def yrs(w):
    if w[3] is None: return None
    ys=[int(y) for y in re.findall(r'(?:notBefore|notAfter|when)="(\d{4})',w[3])]
    if not ys and w[4]:
        ys=[int(y) for y in re.findall(r"\d{4}",w[4])]
    return ys or None
inw=[]
c=collections.Counter()
for w in works:
    y=yrs(w)
    if y is None: c["nodate"]+=1;continue
    lo,hi=min(y),max(y)
    if hi<1450: c["<1450"]+=1
    elif lo>1700: c[">1700"]+=1
    elif lo>=1450 and hi<=1700: c["in"]+=1; inw.append((w,lo,hi))
    else: c["straddle"]+=1
print(c)
json.dump([(w[0],w[1],w[2],lo,hi) for w,lo,hi in inw],open(HARVEST_DIR + "/tg_inwindow.json","w"),ensure_ascii=False)
for w,lo,hi in inw[:60]: print(w[0],w[2][:25],"|",w[1][:50],lo,hi)
