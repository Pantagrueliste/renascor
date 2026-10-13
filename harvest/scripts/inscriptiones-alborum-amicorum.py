import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys,re,json,time,os
HD=HARVEST_DIR + ""
sys.path[:0]=[HD]
from hlib import Harvest, first_year
import iaa_parse as P
from collections import Counter
h=Harvest("inscriptiones-alborum-amicorum",delay=0.5)
B="http://iaa.bibl.u-szeged.hu/index.php?page=browse&entry_id="
recf=h.dir/"files"/"rec.jsonl"
done={}
if recf.exists():
    for l in open(recf,encoding="utf-8"):
        try: r=json.loads(l); done[r["id"]]=r
        except Exception: pass
N=17090
finish_only="--finish-only" in sys.argv
probs=[]
fails=[]
if not finish_only:
    with open(recf,"a",encoding="utf-8") as fh:
        for i in range(1,N+1):
            if i in done: continue
            try: t=h.get(B+str(i))
            except Exception as e:
                time.sleep(3)
                try: t=h.get(B+str(i))
                except Exception as e2: fails.append(i); continue
            p=P.parse(t)
            rec={"id":i,"date":p["date"],"owner":p["owner"],"writer":p["writer"],"parts":p["parts"],"langs":p["langs"]}
            fh.write(json.dumps(rec,ensure_ascii=False)+"\n"); fh.flush(); done[i]=rec
            if i%500==0: print(i,len(fails),time.strftime("%H:%M:%S"),flush=True)
LN=P.LANG
def mainlang(r):
    c=Counter()
    for sec,l in r["langs"]:
        l=l.strip()
        if l in LN: c[(0 if sec=="inscription" else 1,LN[l])]+=1
    if not c: return None
    best=sorted(c.items(),key=lambda kv:(kv[0][0],-kv[1]))[0][0][1]
    return best
notext=0;nodate=0
for i in sorted(done):
    r=done[i]
    txt="\n".join(s for _,s in r["parts"] if s)
    if not txt.strip(): notext+=1; continue
    y=first_year(r["date"]) if r["date"] else None
    if y is None: nodate+=1
    h.add(f"iaa_{i:05d}.txt",txt,language=mainlang(r) or "Latin",year=y,source="Inscriptiones Alborum Amicorum",url=B+str(i),date_text=r["date"],album_owner=r["owner"],writer=r["writer"])
missing=[i for i in range(1,N+1) if i not in done]
if missing: probs.append(f"{len(missing)} entry ids could not be fetched (e.g. {missing[:10]})")
probs.append(f"{notext} entries without transcribed text fields (only metadata/notes) were skipped; {nodate} kept entries have no parseable year (year=None, dateless_in_window=False).")
probs.append("Language = language of the inscription (fallback dedication/signature/motto; 'Latin' if none declared). Texts are short (mottoes, dedications, signatures, verses); Jegyzet (editorial note), Szerző/Cím/Pontos hely (source references) and normalised names were excluded.")
print(h.finish(method="Record-by-record crawl of index.php?page=browse&entry_id=1..17090 (no export, API or OAI found; the search form returned HTTP 500 for scripted queries and each browse page is ~750 KB uncompressed because of the full entry selector). Extracted per entry: motto text, place/date as written, dedication, signature, inscription text and owner's later notes; each entry is one text.",coverage=f"{len(done)} of {N} entries fetched ({len(missing)} missing). All dates 16th-18th c.; only entries dated 1450-1700 count in the window.",problems=probs))
