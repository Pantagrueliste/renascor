import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import glob,re,json,collections
D=str(__import__("hlib").OUT) + "/textgrid-repository/lists/"
ed={}
for f in sorted(glob.glob(D+"editions_*.xml")):
    x=open(f,encoding="utf-8").read()
    for r in re.findall(r"<tgs:result.*?</tgs:result>",x,re.S):
        uri=re.search(r"<textgridUri[^>]*>([^<]+)<",r).group(1)
        w=re.search(r"<isEditionOf>([^<]*)<",r)
        et=re.search(r"<editionTitle>(.*?)</editionTitle>",r,re.S)
        dp=re.search(r"<dateOfPublication[^>]*>(.*?)</dateOfPublication>",r,re.S)
        ext=re.search(r"<extent>(\d+)<",r)
        ed[w.group(1) if w else uri]=(uri,et.group(1).strip() if et else "",re.sub(r"<[^>]+>","",dp.group(1)) if dp else "",int(ext.group(1)) if ext else 0)
json.dump(ed,open(HARVEST_DIR + "/tg_ed.json","w"),ensure_ascii=False)
print(len(ed))
inw=json.load(open(HARVEST_DIR + "/tg_inwindow.json"))
seen=collections.defaultdict(list)
miss=0
for u,t,a,lo,hi in inw:
    e=ed.get(u)
    if not e: miss+=1; continue
    seen[(a,e[1][:110],e[2])].append(e[3])
print("missing",miss,len(seen))
for k,v in sorted(seen.items(),key=lambda kv:-len(kv[1]))[:80]: print(len(v),sum(v),k)
