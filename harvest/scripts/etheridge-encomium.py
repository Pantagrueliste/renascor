import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys,re,html
sys.path[:0]=[HARVEST_DIR + ""]
from hlib import Harvest
h=Harvest("etheridge-encomium")
B="http://hellenic-institute.uk/research/Etheridge/"
ed=h.get(B+"Electronic-Edition/","files/edition.html")
folios=re.findall(r'<option value="(f\d{3}[rv])"',ed)
folios=list(dict.fromkeys(folios))
probs=[];out=[]
for f in folios:
    try: t=h.get(f"{B}Resources/Texts/Transcriptions/royal_ms_16_c_x_{f}.html",f"files/{f}.html")
    except Exception as e: probs.append(f"{f}: {e}"); continue
    t=re.sub(r'</P>','\n',t,flags=re.I); t=re.sub(r'<[^>]+>','',t); t=html.unescape(t)
    t=re.sub(r'[ \t]*\n[ \t]*','\n',t); t=re.sub(r'[ \t]+',' ',t); t=re.sub(r'\n+','\n',t).strip().lstrip('﻿')
    out.append(t)
print(len(folios),len(out))
h.add("etheridge-encomium.txt","\n".join(out),language="Greek",year=1566,source="Etheridge Encomium, BL Royal MS 16 C X (transcription)",url=B)
print(h.finish(method="Per-folio HTML transcription fragments (Resources/Texts/Transcriptions/), discovered from the folio selector of the edition page; tags stripped, concatenated into one text. Edited text, translation and apparatus not used.",coverage=f"{len(out)} of {len(folios)} folio sides.",problems=probs+["Folio-side headings absent; word count may include editorial characters such as '/' used as overlays in the markup; 'c. 1566' given as 1566."]))
