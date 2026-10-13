import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys,re,html
sys.path[:0]=[HARVEST_DIR + ""]
from hlib import Harvest, first_year, slug
h=Harvest("kircher-briefe-herzog-august")
base="http://diglib.hab.de/edoc/ed000005/"
t=h.get(base+"transcription.htm","files/transcription.htm")
# split by the grey header cell containing <a name="P...">
parts=re.split(r'(?=<td valign="top" bgcolor="#cccccc">)',t)
probs=[]
for p in parts[1:]:
    m=re.search(r'<a name="P([^"]+)">[^<]*</a>\s*\((\d{4}-\d\d-\d\d)\)',p)
    if not m: probs.append("unparsed block"); continue
    sig,date=m.groups()
    body=p.split("</td>",1)[1] if "</td>" in p else p
    body=re.split(r'</table>',body)[0]
    body=re.sub(r'<br\s*/?>','\n',body); body=re.sub(r'</p>','\n\n',body)
    body=re.sub(r'<[^>]+>','',body); body=html.unescape(body)
    body=re.sub(r'^\s*\[\d+\]\s*','',body,flags=re.M)
    body=re.sub(r'[ \t]+',' ',body); body=re.sub(r'\n\s*\n+','\n\n',body).strip()
    h.add(f"{slug(sig)}.txt",body,language="Latin",year=first_year(date),source="Kircher an Herzog August (HAB ed000005)",url=base+"transcription.htm#P"+sig,date=date)
print(len(h.records))
print(h.finish(method="HTML transcription page transcription.htm (original text only; line numbers removed; apparatus, translation, commentary pages not used), split per letter.",coverage="All 21 letters on the transcription page (catalogue says 19)." ,problems=probs))
