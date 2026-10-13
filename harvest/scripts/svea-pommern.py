import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys,re,html
sys.path[:0]=[HARVEST_DIR + ""]
from hlib import Harvest, slug
from lxml import html as LH
h=Harvest("svea-pommern")
B="https://svea.geo.uni-greifswald.de/svea/files/xhtml-edition/"
LIMIT=int(sys.argv[1]) if len(sys.argv)>1 else None
probs=[]
sel=h.get(B+"auswahl.html","files/auswahl.html")
names={}   # transcript path -> place names
for tr in re.findall(r'<tr[^>]*>(.*?)</tr>',sel,flags=re.S):
    m=re.search(r'class="Spalte1">\s*([^<]*?)\s*</td>',tr); p=re.search(r'href="([^"]*transkript/[^"]+\.htm)"',tr)
    if m and p: names.setdefault(p.group(1),[]).append(html.unescape(m.group(1)).strip())
paths=sorted(names)
print(len(paths),"unique transcription pages")
def rowtext(td):
    for a in td.xpath('.//span[contains(@class,"footnote_char")]'): a.drop_tree()
    return re.sub(r'\s+',' ',td.text_content()).strip()
n=0
for p in paths:
    if LIMIT and n>=LIMIT: break
    n+=1
    try: t=h.get(B+p,"files/"+p)
    except Exception as e: probs.append(f"{p}: {e}"); continue
    root=LH.fromstring(t.encode("utf-8"))
    sect="main"; buckets={"main":[],"rev":[]}
    for tr in root.xpath('//div[@id="inhalt"]//table/tr|//div[@id="inhalt"]//table/tbody/tr'):
        for a in tr.xpath('.//a[@name]'):
            nm=a.get('name') or ""
            if nm.startswith("txt_"): sect="rev" if "Revision" in nm else "main"
        tds=tr.xpath('./td')
        if len(tds)<3: continue
        if rowtext(tds[1]) in ("Zeile",): continue
        line=rowtext(tds[2]); extra=rowtext(tds[3]) if len(tds)>3 else ""
        s=(line+" "+extra).strip()
        if s: buckets[sect].append(s)
    base=slug(p.split("/")[-1].replace("_trans.htm",""))
    place=" / ".join(names[p])
    for kind,lines in buckets.items():
        if not lines: continue
        raw="\n".join(lines)
        if kind=="main":
            m=re.search(r'(?<!\d)(169\d)(?!\d)',"\n".join(lines[:6]))
            if m: h.add(f"{base}.txt",raw,language="Swedish",year=int(m.group(1)),source=f"SVEA-Pommern: {place}",url=B+p,place=place,part="Hauptvermessung")
            else: h.add(f"{base}.txt",raw,language="Swedish",year=None,dateless_in_window=True,source=f"SVEA-Pommern: {place}",url=B+p,place=place,part="Hauptvermessung")
        else:
            m=re.search(r'(?<!\d)(17[01]\d)(?!\d)',"\n".join(lines[:8]))
            h.add(f"{base}_rev.txt",raw,language="Swedish",year=int(m.group(1)) if m else 1705,source=f"SVEA-Pommern: {place} (Revision 1704/05)",url=B+p,place=place,part="Revision")
print(h.finish(method="Place list (files/xhtml-edition/auswahl.html) -> one HTML transcription page per place (shared pages deduplicated). Kept the fair-copy (Reinschrift) transcription column plus the adjacent column of contemporary marginal additions; footnote markers and the footnotes, the German translation (uebers) and the draft-copy (Urschrift) folio markers dropped. Each page split into the main survey and the 1704/05 revision at the revision section anchor.",coverage=f"{len(h.records)} texts from {n} of {len(paths)} unique transcription pages ({sum(len(v) for v in names.values())} place entries).",problems=probs+["The pages show the Reinschrift transcription only (the Urschrift/draft folios are mapped by markers in the same table, not separately transcribed), so no draft/fair duplicates. Main-survey year taken from the first 169x year in the opening lines; where none, year=None with dateless_in_window=True because the main survey is documented as 1692-1698. Revision texts (1704/05) fall after 1700 and are kept with their year (out of window)."]))
