import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, json, glob, time
sys.path.insert(0,HARVEST_DIR + "")
from hlib import Harvest, slug
D=str(__import__("hlib").OUT) + "/textgrid-repository/lists/"
ed=json.load(open(HARVEST_DIR + "/tg_ed.json"))
MANUAL={ # work uri -> year, for undated works whose source date is known from the edition/title
 "textgrid:jn87.0":1521,"textgrid:jndb.0":1509,"textgrid:jnhf.0":1582,"textgrid:jnjk.0":1597,"textgrid:jnkc.0":1687,
 "textgrid:jnkv.0":1587,"textgrid:jnpz.0":1602,"textgrid:n7sc.0":1516,"textgrid:n7sf.0":1516,"textgrid:n7sk.0":1516,
 "textgrid:ngs9.0":1700,"textgrid:r233.0":1532,"textgrid:szjv.0":1522,
 "textgrid:t9q7.0":1696,"textgrid:t9q9.0":1696,"textgrid:t9qg.0":1700,"textgrid:t9qm.0":1695,
 "textgrid:v3n9.0":1540,"textgrid:v3nc.0":1547,"textgrid:v3nk.0":1547,"textgrid:v3nr.0":1543,
 "textgrid:vmm7.0":1538,"textgrid:wz14.0":1538,
 "textgrid:x8b6.0":1554,"textgrid:x8b8.0":1555,"textgrid:x8bf.0":1556,"textgrid:x8bk.0":1540,"textgrid:x8bt.0":1537,"textgrid:x8c0.0":1551}
LANG={"deu":"German","lat":"Latin","fra":"French","ita":"Italian","eng":"English","nds":"German","gsw":"German"}
works=[]
for f in sorted(glob.glob(D+"works_*.xml")):
    x=open(f,encoding="utf-8").read()
    for r in re.findall(r"<tgs:result.*?</tgs:result>",x,re.S):
        uri=re.search(r"<textgridUri[^>]*>([^<]+)<",r).group(1)
        t=re.search(r"<title>(.*?)</title>",r,re.S).group(1)
        a=re.search(r'<agent role="author"[^>]*>([^<]*)<',r); a=a.group(1) if a else ""
        d=re.search(r"<dateOfCreation([^>]*)>([^<]*)<",r)
        ys=[int(y) for y in re.findall(r'(?:notBefore|notAfter|when)="(\d{4})',d.group(1))] if d else []
        works.append((uri,t,a,ys))
TR=re.compile(r"Übers|übers|Übertr|übertr|Aus dem|Bearbeitung")
sel=[];skipped_tr=0;strad=0;total_dated=0
for uri,t,a,ys in works:
    e=ed.get(uri)
    if not e: continue
    if uri in MANUAL: y=MANUAL[uri]
    elif ys:
        lo,hi=min(ys),max(ys)
        if lo<1450 or hi>1700: 
            if lo<=1700 and hi>=1450 and not(lo<1450 and hi<1450): strad+=1
            continue
        y=(lo+hi)//2
    else: continue
    if a.startswith("Plavius") : y=1630
    if TR.search(e[1]) and not a.startswith("Abschatz"):
        skipped_tr+=1; continue
    sel.append((uri,t,a,y,e))
print("selected",len(sel),"translation-skipped",skipped_tr,"straddle",strad,flush=True)
import urllib.parse
h=Harvest("textgrid-repository",delay=0.5)
P="TGPR-372fe6dc-57f2-6cd4-01b5-2c4bbefcfd3c"
selmap={e[0]:(uri,t,a,y) for uri,t,a,y,e in sel}
authors=sorted({a for _,_,a,_,_ in sel if a and not a.startswith("Anonym")})
xml_of={}
for a in authors:
    start=0
    while True:
        u="https://textgridlab.org/1.0/tgsearch-public/search?"+urllib.parse.urlencode({"q":'edition.agent.value:"'+a+'"',"limit":200,"start":start,"path":"true","filter":["project.id:"+P,"format:text/xml"]},doseq=True)
        x=h.get(u,"lists/xml/"+slug(a)+"_"+str(start)+".xml")
        n=len(re.findall(r"<tgs:result ",x))
        for xu,body in re.findall(r'<tgs:pathGroup startUri="([^"]+)">(.*?)</tgs:pathGroup>',x,re.S):
            ents=re.findall(r"<tgs:textgridUri>([^<]+)<",body)
            if ents and ents[-1] in selmap: xml_of[ents[-1]]=xu
        if n<200: break
        start+=200
    print(a,len(xml_of),flush=True)
for ed,(uri,t,a,y) in selmap.items():
    if ed not in xml_of and (a.startswith("Anonym") or uri in MANUAL):
        try:
            x=h.get("https://textgridlab.org/1.0/tgsearch-public/navigation/agg/"+ed,"lists/nav/"+slug(ed)+".xml")
            m=re.search(r"<format>text/xml</format>.*?<textgridUri[^>]*>([^<]+)<",x,re.S)
            if m: xml_of[ed]=m.group(1)
        except Exception as ex: print("nav fail",ed,ex)
print("mapped",len(xml_of),"of",len(selmap),flush=True)
fails=[];unmapped=[ed for ed in selmap if ed not in xml_of]
for i,(ed,xu) in enumerate(xml_of.items()):
    uri,t,a,y=selmap[ed]
    try:
        raw=h.get("https://textgridlab.org/1.0/tgcrud-public/rest/"+xu+"/data","tei/"+slug(xu)+".xml")
    except Exception as ex:
        fails.append((xu,str(ex)[:80])); continue
    m=re.search(r'<language ident="([^"]+)"',raw)
    lang=LANG.get(m.group(1)[:3],"German") if m else "German"
    h.add(slug(xu)+".xml",raw,language=lang,year=y,source="TextGrid Digitale Bibliothek: "+a+": "+t[:80],url="https://textgridrep.org/"+xu)
    if i%500==0: print(i,len(xml_of),time.strftime("%H:%M:%S"),flush=True)
OTHER='adso (TGPR-45581d1b-1326-48e5-e607-69d5da02b3f3, Spanish Golden Age poetry): 2,321 works dated wholly 1450-1700 (+102 straddling), e.g. Herrera 320, Cetina 248, Villamediana 203, Argensola 158; textbox_32 (TGPR-4b8bf6c0-e82e-285f-9f69-66bee06b5e2f, French theatre, Corneille/Scarron/Moliere): 98 in-window works (+290 later); a second project also named Digitale Bibliothek (TGPR-e4123902-183d-2f76-9b8f-2abbc96391d9): 9 in-window (Heinrich Julius, Grimmelshausen, Ziegler), 440 later, 334 undated; Kolimo+ (41,298 works, 19th-20th c., none in window), Multilingual Bible Corpus (4,912, out of window), ELTeC (1,262, 19th c.), gretil (1,171, Sanskrit), Goethe Farbenlehre reception (1,340), American Drama Corpus (771, 19th-20th c.): 0 in-window'
probs=[
 "Years: work metadata dateOfCreation is, for most authors, the author's active/life span rather than the date of the individual text; year = midpoint of a range lying entirely within 1450-1700 (e.g. Logau 1605-1655 -> 1630). Texts are mostly modern scholarly editions of period texts (Eitner 1872, Szyrocki, Milch, etc.); each poem/epigram/play is its own record; some editorial apparatus may remain inside <text>.",
 str(strad)+" works whose date range straddles 1450 or 1700 (mostly authors of c.1690-1770 such as Tersteegen, Wernicke, Zinzendorf, Guenther, Hunold, Brockes, Stieler, Weise) were excluded as not wholly in-window and not fetched.",
 str(skipped_tr)+" in-window works excluded as modern translations into German (Shakespeare/Schloesser, La Fontaine/Etzel, Montaigne/Bode, Navarra/Foerster, Moliere, Corneille, Cervantes, Calderon, Ariosto, etc.).",
 "About 5,200 Digitale Bibliothek works carry no usable date; ~30 of them (Wickram, Gengenbach, Pauli, Schmeltzl, Reuter, Lalebuch 1597, Faustbuch 1587, Fortunatus 1509, Ambraser Liederbuch 1582, Karsthans 1521, etc.) were dated by hand from edition titles/known publication dates, and Johannes Plavius (197 poems) set to approximate 1630. Remaining undated works (Kuhn, Grimm, Schambach, Arent, 18th-19th c. anonymous anthologies, ancient authors in translation) are not period texts and were not harvested; a few undated 16th-17th c. items (Pickelherings Spiel, Muenchner Spiel vom sterbenden Menschen, Kraeutlein Toback) were left out.",
 "Because tgsearch work-level dates are author spans, the 1450-1700 selection is approximate: some later-printed texts by in-window authors may be included and some in-window texts by authors with wider spans are excluded.",
 "Other public TextGrid projects (work counts from tgsearch-public; facet shows only the 10 largest projects, so smaller ones may be missing): "+OTHER,
 str(len(unmapped))+" selected editions could not be mapped to an XML object; "+str(len(fails))+" fetch failures."]+["fetch failed "+u+": "+m for u,m in fails[:20]]
rep=h.finish(method="TextGrid tgsearch-public: all 93,675 works of the Digitale Bibliothek project listed (5000/page) with dateOfCreation; in-window works joined to editions; XML object ids found via search path=true per author, TEI downloaded from tgcrud-public (/rest/<uri>/data), 0.5 s between requests. aggregator/teicorpus was too slow and /zip is blocked.",
 coverage="Digitale Bibliothek only: "+str(len(sel))+" in-window works selected from 93,675 (by work dateOfCreation, translations excluded); "+str(len(h.records))+" fetched. Other TextGrid projects (adso, textbox_32, Kolimo+, etc.) not harvested.",problems=probs)
print(json.dumps({k:rep[k] for k in("texts_in_window","words_in_window","texts_total","words_total")}))
