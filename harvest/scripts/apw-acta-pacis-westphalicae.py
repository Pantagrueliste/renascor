import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, json, html, time, urllib.parse
HD = HARVEST_DIR + ""
sys.path.insert(0, HD)
from hlib import Harvest, first_year
from lxml import etree
RID = "apw-acta-pacis-westphalicae"
h = Harvest(RID)
B = "https://apw.digitale-sammlungen.de"
problems = []
TEI = "{http://www.tei-c.org/ns/1.0}"
XMLLANG = "{http://www.w3.org/XML/1998/namespace}lang"
consec_fail = 0
DEADLINE = time.time() + 4.0 * 3600   # wall-clock budget for the document crawl
stopped = False
_orig_get = h.s.get
h.s.get = lambda url, **kw: _orig_get(url, **{**kw, "timeout": 15})

def robust_get(url, rel, tries=8):
    """h.get with backoff on 5xx/timeouts (the BSB server returns 502 / maintenance page intermittently)."""
    global consec_fail
    for a in range(tries):
        try:
            s = h.get(url, rel)
            if "<title>Wartungsarbeiten" in s[:600]:
                raise RuntimeError("maintenance page")
            consec_fail = 0
            return s
        except Exception as e:
            consec_fail += 1
            wait = (min(60, 5 * 2 ** a) if consec_fail < 10 else 120) if tries > 1 or consec_fail >= 10 else 0
            print(f"retry {rel} ({e.__class__.__name__}: {str(e)[:80]}) sleep {wait}", file=sys.stderr, flush=True)
            # remove a cached maintenance page if any
            p = h.dir / rel
            if p.exists() and "<title>Wartungsarbeiten" in p.read_text(errors="replace")[:600]: p.unlink()
            time.sleep(wait)
    return None

home = robust_get(B + "/search/query.html?start=0&rows=10", "files/list/home.html")
vols = []
for m in re.findall(r'query\.html\?titleAPW_str=([^"&]*)', home):
    v = html.unescape(m).replace("+", " ")
    if v not in vols: vols.append(v)

def parse_list(s):
    out = []
    for li in re.finditer(r'<li id="record\.([^"]+)" class="record".*?</li>', s, re.S):
        txt = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", li.group(0)))).strip()
        out.append((li.group(1), txt))
    return out

recs = {}
for v in vols:
    vk = re.sub(r"[^A-Za-z0-9]+", "_", v)
    start, total, rows = 0, None, 100
    got = []
    while total is None or start < total:
        url = f"{B}/search/query.html?" + urllib.parse.urlencode({"titleAPW_str": v, "start": start, "rows": rows})
        s = robust_get(url, f"files/list/{vk}_{start}.html", tries=4 if total else 8)
        if s is None:
            # fall back to small pages for this range
            ok = True
            for st in range(start, min(start + rows, total or start + rows), 10):
                u2 = f"{B}/search/query.html?" + urllib.parse.urlencode({"titleAPW_str": v, "start": st, "rows": 10})
                s2 = robust_get(u2, f"files/list/{vk}_{st}_r10.html", tries=3)
                if s2 is None:
                    problems.append(f"{v}: listing records {st}-{st+9} could not be fetched (HTTP 502)")
                else:
                    got += parse_list(s2)
            start += rows
            continue
        if total is None:
            total = int(re.search(r"ergab (\d+) Dokument", s).group(1))
        got += parse_list(s)
        start += rows
    recs[v] = got
    print(v, total, len(got), file=sys.stderr, flush=True)

def lang_of(vol, subtype, xml):
    langs = {}
    for el in xml.iter():
        l = el.get(XMLLANG)
        if l:
            n = len("".join(el.itertext()))
            langs[l[:2]] = langs.get(l[:2], 0) + n
    names = {"de": "German", "fr": "French", "la": "Latin", "sv": "Swedish", "it": "Italian", "es": "Spanish", "nl": "Dutch"}
    if langs:
        top = max(langs, key=langs.get)
        if top in names: return names[top]
    st = (subtype or "").lower()
    if "french" in st or " II B" in vol: return "French"
    if "swed" in st: return "Swedish"
    if "latin" in st: return "Latin"
    return "German"

ndocs = nfail = 0
failed_ids = set()
for pass_no in (1, 2):
  for v in vols:
    if stopped: break
    for rid, txt in recs[v]:
        if "_dok" not in rid: continue
        if pass_no == 2 and rid not in failed_ids: continue
        if pass_no == 2 and (rid + ".xml") in h.seen: continue
        if pass_no == 1: ndocs += 1
        if time.time() > DEADLINE:
            stopped = True
            break
        s = robust_get(f"{B}/ObjectComponent/project.getObject?id={rid}", f"files/doc/{rid}.xml", tries=1 if pass_no == 1 else 3)
        if s is None:
            failed_ids.add(rid)
            if pass_no == 2: nfail += 1; problems.append(f"{rid}: fetch failed twice (HTTP 502/504 from the server)")
            continue
        try:
            root = etree.fromstring(s.encode("utf-8"))
        except Exception as e:
            problems.append(f"{rid}: parse error {e}"); continue
        # date from the dating block before it is removed
        dt = root.xpath(".//t:div[@type='desc' and @subtype='dating']//t:date/@when", namespaces={"t": TEI[1:-1]})
        year = first_year(dt[0]) if dt else None
        if year is None:
            dt2 = root.xpath(".//t:date/@when | .//t:date/@notBefore", namespaces={"t": TEI[1:-1]})
            year = first_year(dt2[0]) if dt2 else None
        if year is None:
            m = re.search(r"(?<!\d)(16[0-9]\d)(?!\d)", txt.split("[")[0] + " " + txt)
            year = int(m.group(1)) if m else None
        subtype = root.get("subtype")
        language = lang_of(v, subtype, root)
        # drop modern editorial parts: headings, descriptions (dating, transmission, docNum), footnotes
        kill = root.xpath(".//t:div[@type='head'] | .//t:div[@type='desc'] | .//t:note[@type='edd'] | .//t:note[@place='foot']", namespaces={"t": TEI[1:-1]})
        for el in kill:
            par = el.getparent()
            if par is None: continue
            tail = el.tail
            prev = el.getprevious()
            if tail:
                if prev is not None: prev.tail = (prev.tail or "") + tail
                else: par.text = (par.text or "") + tail
            par.remove(el)
        for el in list(root.iter(TEI + "expan")):
            par = el.getparent(); tail = el.tail; prev = el.getprevious()
            if tail:
                if prev is not None: prev.tail = (prev.tail or "") + tail
                else: par.text = (par.text or "") + tail
            par.remove(el)
        raw = "<TEI><text><body>" + etree.tostring(root, encoding="unicode") + "</body></text></TEI>"
        h.add(rid + ".xml", raw, language=language, year=year, source=f"APW {v}: {txt[:110]}", url=f"{B}/search/display.html?id={rid}", volume=v)
        if ndocs % 500 == 0: print("docs", ndocs, "fail", nfail, file=sys.stderr, flush=True)
rep = h.finish(method="Search listing per volume (/search/query.html?titleAPW_str=<vol>&rows=100) to enumerate all 'dok' records, then per-document TEI XML (/ObjectComponent/project.getObject?id=<id>); removed modern editorial parts (headings, dating/transmission/docNum description divs, foot notes of type edd, expansions of abbreviations); kept the document text (original abbreviations as printed in the edition).",
  coverage=(f"{len(h.records)} of {sum(1 for v in vols for r, _ in recs[v] if '_dok' in r)} document records listed in the 41 online volumes were fetched" + (" (crawl stopped at a self-imposed time budget because the BSB server answered intermittently with 502/504; volumes are processed in the order of the search facet, so the later volumes are missing: see the last fetched volume in staging)" if stopped else "") + f"; {nfail} fetches failed twice. Excluded by design: introductions, prefaces, source lists, registers (sec records), headings, archival descriptions and footnotes of the edition."),
  problems=problems[:40] + ["The edition is a modern critical edition of period documents; the German text in Series I-III is the archival original (German, French, Latin, Swedish), but editorial insertions in square brackets and the line-break hyphenation of the printed edition remain in the text.",
     "Year from the document's dateline (date@when); documents without date fall back to a year in the title."])
print(json.dumps({k: rep[k] for k in ("texts_total","words_total","texts_in_window","words_in_window","undated")}))
