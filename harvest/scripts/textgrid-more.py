import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys,re,json,glob,urllib.parse
sys.path.insert(0,HARVEST_DIR + "")
from hlib import Harvest, slug
D=str(__import__("hlib").OUT) + "/textgrid-repository/"
old=json.load(open(D+"report.json"))
recs=[json.loads(l) for l in open(D+"staging.jsonl")]
h=Harvest("textgrid-repository",delay=0.5)
h.records=recs; h.seen={r["filename"] for r in recs}
B="https://textgridlab.org/1.0/tgsearch-public/search?"
PR={"adso":("TGPR-45581d1b-1326-48e5-e607-69d5da02b3f3","Spanish"),
    "textbox32":("TGPR-4b8bf6c0-e82e-285f-9f69-66bee06b5e2f","French"),
    "digbib2":("TGPR-e4123902-183d-2f76-9b8f-2abbc96391d9","German")}
LANG={"deu":"German","lat":"Latin","fra":"French","spa":"Spanish","ita":"Italian","eng":"English"}
TR=re.compile(r"Übers|übers|Übertr|übertr|Aus dem")
def pages(P,fmt,name,extra={}):
    s=0;out=[]
    while True:
        q={"q":"*","limit":200,"start":s,"filter":["project.id:"+P,"format:"+fmt]};q.update(extra)
        x=h.get(B+urllib.parse.urlencode(q,doseq=True),"lists/more/%s_%s_%d.xml"%(name,slug(fmt),s))
        rs=re.findall(r"<tgs:result.*?</tgs:result>",x,re.S)
        out.append(x)
        if len(rs)<200: break
        s+=200
    return out
info=[];added={};lang_note=[]
for name,(P,dl) in PR.items():
    works={}
    for x in pages(P,"text/tg.work+xml",name+"_w"):
        for r in re.findall(r"<tgs:result.*?</tgs:result>",x,re.S):
            u=re.search(r"<textgridUri[^>]*>([^<]+)<",r).group(1)
            t=re.search(r"<title>(.*?)</title>",r,re.S).group(1)
            a=re.search(r'<agent role="author"[^>]*>([^<]*)<',r); d=re.search(r"<dateOfCreation([^>]*)>",r)
            ys=[int(y) for y in re.findall(r'(?:notBefore|notAfter|when)="(-?\d{4})',d.group(1))] if d else []
            if ys and min(ys)>=1450 and max(ys)<=1700: works[u]=(t,a.group(1) if a else "",(min(ys)+max(ys))//2)
    eds={}
    for x in pages(P,"text/tg.edition+tg.aggregation+xml",name+"_e"):
        for r in re.findall(r"<tgs:result.*?</tgs:result>",x,re.S):
            u=re.search(r"<textgridUri[^>]*>([^<]+)<",r).group(1)
            w=re.search(r"<isEditionOf>([^<]*)<",r); et=re.search(r"<editionTitle>(.*?)</editionTitle>",r,re.S)
            if w and w.group(1) in works: eds[u]=(w.group(1),et.group(1) if et else "")
    n=0;tr=0
    for x in pages(P,"text/xml",name+"_x",{"path":"true"}):
        for xu,body in re.findall(r'<tgs:pathGroup startUri="([^"]+)">(.*?)</tgs:pathGroup>',x,re.S):
            ents=re.findall(r"<tgs:textgridUri>([^<]+)<",body)
            if not ents or ents[-1] not in eds: continue
            wu,et=eds[ents[-1]]
            if TR.search(et): tr+=1; continue
            t,a,y=works[wu]
            raw=h.get("https://textgridlab.org/1.0/tgcrud-public/rest/"+xu+"/data","tei/%s/%s.xml"%(name,slug(xu)))
            m=re.search(r'<language ident="([^"]+)"',raw)
            lg=LANG.get(m.group(1)[:3],dl) if m else dl
            h.add("%s/%s.xml"%(name,slug(xu)),raw,language=lg,year=y,source="TextGrid %s: %s: %s"%(name,a,t[:80]),url="https://textgridrep.org/"+xu)
            n+=1
    added[name]=(len(works),len(eds),n,tr); print(name,added[name],flush=True)
probs=old["problems"]+["Appended projects (same dating rule: work dateOfCreation range wholly within 1450-1700, year = midpoint; translations excluded by edition title): "+"; ".join("%s: %d in-window works, %d editions, %d texts added, %d translations skipped"%(k,*v) for k,v in added.items())+". adso years are author spans (e.g. Herrera), so approximate; textbox32 and the second Digitale Bibliothek project likewise."]
rep=h.finish(method=old["method"]+" Then appended three further public TextGrid projects (adso, textbox_32, second Digitale Bibliothek) with the same procedure (works list -> editions -> search path=true -> tgcrud data).",
 coverage=old["coverage"].replace("Digitale Bibliothek only:","Digitale Bibliothek TGPR-372fe6dc (main part), plus in-window works of adso, textbox_32 and the second Digitale Bibliothek project TGPR-e4123902:").replace("Other TextGrid projects (adso, textbox_32, Kolimo+, etc.) not harvested.","Not harvested: Kolimo+, ELTeC, Bible Corpus, gretil, American Drama, Farbenlehre (no period material) and any project too small to appear in the top-10 facet."),problems=probs)
print(json.dumps({k:rep[k] for k in("texts_in_window","words_in_window","texts_total")}),rep["language_words"])
