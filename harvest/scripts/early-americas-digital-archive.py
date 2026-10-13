import os as _os; HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
sys.path.insert(0, HARVEST_DIR)
from hlib import Harvest, tei_year, first_year, slug
import re, json, time, hashlib
from bs4 import BeautifulSoup

h = Harvest("early-americas-digital-archive", delay=1.5)
problems = []
HOST = "mith.umd.edu/eada"

def wb_get(url, rel, tries=4):
    for i in range(tries):
        try:
            return h.get(url, rel)
        except Exception as e:
            if any(c in str(e) for c in ("429", "500", "502", "503", "504", "Timeout", "Connection")):
                time.sleep(15 * (i + 1)); continue
            raise
    raise RuntimeError("gave up: " + url)

# 1. CDX listing of captured pages of the original site (cached)
rel = "files/cdx_mith.json"
if (h.dir / rel).exists():
    rows = json.loads((h.dir / rel).read_text())
else:
    q = ("https://web.archive.org/cdx/search/cdx?url=" + HOST + "&matchType=prefix&output=json"
         "&fl=timestamp,original,mimetype,statuscode&filter=statuscode:200&limit=50000")
    rows = json.loads(wb_get(q, rel))
rows = rows[1:]
docs, gate = {}, {}
for ts, u, m, s in rows:
    if m != "text/html":
        continue
    mm = re.search(r"display\.php\?docs=([^&#]+)", u)
    if mm:
        k = mm.group(1).lower()
        if k not in docs or ts > docs[k][0]:
            docs[k] = (ts, u)
        continue
    g = re.search(r"/eada/gateway/([a-z0-9_]+)\.php$", u.split("?")[0].lower())
    if g:
        k = g.group(1)
        if k not in gate or ts > gate[k][0]:
            gate[k] = (ts, u)
docs.pop("bradford", None); docs.pop("removed", None)

def raw_url(ts, u):
    return f"https://web.archive.org/web/{ts}id_/{u}"

# 2. expected texts = display.php?docs=... links found on the captured author gateway pages
expected = set()
for k, (ts, u) in sorted(gate.items()):
    try:
        g = wb_get(raw_url(ts, u), f"files/gateway/{k}.html")
    except Exception as e:
        continue
    expected |= {x.lower() for x in re.findall(r"display\.php\?docs=([A-Za-z0-9_]+\.xml)", g)}

# 3. Per text: year of the source text (hand-set from the author/work), and translation flag
TRANSLATION = {  # English translations made in the 19th-20th c. of Spanish, Portuguese, French, Dutch, Swedish originals: skipped
    "acrelius_founding.xml", "bello_agriculture.xml", "biedma_relation.xml", "cabeza_eng.xml", "castaneda_account.xml",
    "champlain_founding.xml", "columbus_4thvoyage.xml", "columbus_journal.xml", "columbus_santangel.xml", "cortez_letter2.xml",
    "dominguez_journal.xml", "elvas_narrative.xml", "erauso_autobiography.xml", "garcilaso_florida.xml", "heredia_niagara_eng.xml",
    "lopez_de_mendoza_staugustine.xml", "manzano_life.xml", "ranjel_relation.xml", "siguenza_mercurio.xml", "siguanza_mercurio.xml",
    "sorjuana_arraignment.xml", "sorjuana_caprice.xml", "sorjuana_lostlove.xml", "sorjuana_tarry.xml", "sorjuana_toherportrait.xml",
    "steendam_complaint.xml", "vespucci_letters.xml",
}
PLACEHOLDER = {"arabic.xml", "poetryexample.xml"}
NEARDUP = {"lascasas_sepulveda_disputa.xml": "lascasas_sepulveda.xml", "titucusi_instruccion1.xml": "titucusi_instruccion.xml"}  # same text, second copy skipped
YEAR = {
 "alsop_character.xml":1666,"ashbridge_account.xml":1774,"banneker_letter.xml":1791,"barlow_anarchiad.xml":1787,"barlow_conspiracy.xml":1792,
 "barlow_vision.xml":1787,"barlowe_voyage.xml":1584,"bartram_travels.xml":1791,"bello_agricultura.xml":1826,"berkeley_discourse.xml":1663,
 "bradford_history.xml":1650,"bradstreet_anotheri.xml":1678,"bradstreet_anotherii.xml":1678,"bradstreet_author.xml":1678,
 "bradstreet_beforethebirth.xml":1678,"bradstreet_contemplations.xml":1678,"bradstreet_deliverance.xml":1678,"bradstreet_dialogue.xml":1650,
 "bradstreet_fourages.xml":1650,"bradstreet_herefollow.xml":1678,"bradstreet_inhonor.xml":1650,"bradstreet_inmemory.xml":1678,
 "bradstreet_inmysolitary.xml":1678,"bradstreet_prologue.xml":1650,"bradstreet_tomydear.xml":1678,"bradstreet_tomydearchildren.xml":1678,
 "bradstreet_uponburning.xml":1678,"byrd_history.xml":1728,"byrd_journey.xml":1733,"byrd_progress.xml":1732,"cabeza_ms1.xml":1545,
 "cabeza_ms2.xml":1555,"cabeza_sp.xml":1542,"cooke_sotweed.xml":1708,"cooke_sotweedrediv.xml":1730,"crevecoeur_letters.xml":1782,
 "dominguez_diario.xml":1776,"dwight_conquestofcanaan.xml":1785,"dwight_greenfieldhill.xml":1794,"dwight_triumph.xml":1788,
 "edwards_personalnarrative.xml":1740,"equiano_narrative.xml":1789,"erauso_historia.xml":1625,"franklin_autobiography.xml":1791,
 "franklin_bagatelle1.xml":1779,"franklin_bagatelle2.xml":1780,"franklin_bagatelle3.xml":1784,"franklin_bagatelle4.xml":1782,
 "freneau_deathoffranklin.xml":1790,"freneau_honeybee.xml":1809,"freneau_indian.xml":1788,"freneau_onretirement.xml":1781,
 "freneau_risingglory.xml":1772,"freneau_wildhoney.xml":1786,"grainger_sugarcane.xml":1764,"hamilton_itinerarium.xml":1744,
 "hariot_report.xml":1588,"hayes_voyage.xml":1583,"heredia_niagara.xml":1825,"horne_briefcarolina.xml":1666,"knight_journal.xml":1704,
 "lascasas_sepulveda.xml":1552,"lascasas_sepulveda_disputa.xml":1552,"lewis_journey.xml":1730,"morton_newenglishcanaan.xml":1637,
 "murray_equality.xml":1790,"olmedo_victoria.xml":1825,"pastorius_description.xml":1700,"penn_fruits.xml":1693,"raleigh_discovery.xml":1596,
 "raleigh_discovery1.xml":1596,"rowlandson_narrative.xml":1682,"smith_map.xml":1612,"smith_truerelation.xml":1608,"steendam_klagt.xml":1659,
 "taylor_addresstothesoul.xml":1685,"taylor_godsdeterinsufficiency.xml":1685,"taylor_godsdeterjoy.xml":1685,"taylor_godsdeterpreface.xml":1685,
 "taylor_godsdeterprologue.xml":1685,"taylor_huswifery.xml":1685,"taylor_meditations1.xml":1682,"taylor_meditations35.xml":1685,
 "taylor_meditations60.xml":1690,"taylor_meditations8.xml":1682,"taylor_reflexion.xml":1685,"titucusi_instruccion.xml":1570,
 "titucusi_instruccion1.xml":1570,"tyler_contrast.xml":1787,"wheatley_letter.xml":1773,"wheatley_niobe.xml":1773,
 "wheatley_onthedeathoftherevdrsewell.xml":1769,"wheatley_onthedeathoftherevmrgeorge.xml":1770,"wheatley_preface.xml":1773,
 "wheatley_providence.xml":1773,"wheatley_tothepublick.xml":1773,"woolman_journal.xml":1774,"yeardley_narrative.xml":1654,
}  # no year (None, counted out): occom_398/457 (undated 18th-c. sermons), revel_poor (c.1800), wilson_poems (c.1800)
LANG = {"cabeza_ms1.xml":"Spanish","cabeza_ms2.xml":"Spanish","cabeza_sp.xml":"Spanish","dominguez_diario.xml":"Spanish",
        "erauso_historia.xml":"Spanish","lascasas_sepulveda.xml":"Spanish","lascasas_sepulveda_disputa.xml":"Spanish",
        "titucusi_instruccion.xml":"Spanish","titucusi_instruccion1.xml":"Spanish","olmedo_victoria.xml":"Spanish",
        "bello_agricultura.xml":"Spanish","heredia_niagara.xml":"Spanish","steendam_klagt.xml":"Dutch"}

def body_text(html):
    i = html.find("Full Colophon")
    j = html.find("<hr", i if i >= 0 else 0)
    frag = html[j:] if j >= 0 else html
    k = frag.rfind("</td></tr></table>")
    frag = frag[:k] if k > 0 else frag
    soup = BeautifulSoup(frag, "lxml")
    for t in soup(["script", "style", "form"]):
        t.decompose()
    for t in soup.select("span.numbering-line"):
        t.decompose()
    for br in soup.find_all("br"):
        br.replace_with("\n")
    txt = soup.get_text(" ")
    txt = re.sub(r"[ \t\r\f\v]+", " ", txt)
    txt = re.sub(r"\n\s*\n+", "\n", re.sub(r" ?\n ?", "\n", txt)).strip()
    return txt

skipped_tr, skipped_ph, dups, failed, n_ok = [], [], [], [], 0
hashes = {}
for k, (ts, u) in sorted(docs.items()):
    if k in PLACEHOLDER:
        skipped_ph.append(k); continue
    if k in NEARDUP:
        dups.append(f"{k} ~ {NEARDUP[k]} (near-identical)"); continue
    if k in TRANSLATION:
        skipped_tr.append(k); continue
    try:
        html = wb_get(raw_url(ts, u), f"files/{k}.html")
    except Exception as e:
        failed.append(k); problems.append(f"{k}: {str(e)[:80]}"); continue
    txt = body_text(html)
    if len(txt.split()) < 20:
        problems.append(f"{k}: no text extracted"); continue
    dg = hashlib.md5(txt.encode()).hexdigest()
    if dg in hashes:
        dups.append(f"{k} = {hashes[dg]}"); continue
    hashes[dg] = k
    m = re.search(r"<h3>(.*?)</h3>", html, re.S)
    title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).replace("An Electronic Edition", "").strip() if m else k
    h.add(k.replace(".xml", "") + ".txt", txt, language=LANG.get(k, "English"), year=YEAR.get(k),
          source=f"EADA: {title}", url=raw_url(ts, u))
    n_ok += 1

cap = len(set(docs) - PLACEHOLDER)
exp_n = len(expected) or cap
share = f"{100*len(expected & set(docs))/len(expected):.0f}%" if expected else "n/a"
rep = h.finish(
    method="Listed captures of the original MITH site (mith.umd.edu/eada) with the Wayback CDX API, picked the latest 200 capture of each text page html/display.php?docs=<id>.xml, and downloaded the raw capture (id_ form) at 1.5 s intervals. Extracted the text after the colophon header, dropping navigation, search form and line-number marks. One record per EADA text (poem, letter, narrative). Years are set by hand from the work's date of composition/first publication (the page gives only author dates and the source edition).",
    coverage=f"{n_ok} texts stored from {len(docs)} captured text pages; the author gateway pages captured by the Wayback Machine link to {len(expected)} text ids, {len(expected & set(docs))} of which have a captured text page ({share}). The later eada.lib.umd.edu WordPress site (161 text-entries pages, mostly eighteenth-century with modern introductions) was not harvested. Skipped: {len(skipped_tr)} texts that are modern English translations of Spanish/French/Dutch/Swedish originals, {len(skipped_ph)} placeholder pages, {len(dups)} exact duplicates ({'; '.join(dups)}).",
    problems=problems + [
        "Skipped as modern-English translations (rewritten language, not original/normalised text): " + ", ".join(sorted(skipped_tr)),
        "Texts are modern editions in normalised or original spelling (Bradford, Taylor, Hariot, Smith, Raleigh, Rowlandson in original spelling; Penn, Hayes, Berkeley etc. from early-twentieth-century editions with possible modernisation); not all spelling regimes could be verified.",
        "Most of the archive is eighteenth- or nineteenth-century (Franklin, Freneau, Wheatley, Barlow ...): these are kept in staging with their years so that they are counted out.",
        "Occom (2 sermons), Revel and Wilson have no year (undated eighteenth/early nineteenth century): year=None, dateless_in_window=False.",
        "Years for Bradstreet (publication 1650/1678) and Taylor (c. 1682-1690) are approximate; Taylor's Meditation 60 date is uncertain.",
        "The TEI sources are not available from the Wayback Machine; text taken from rendered HTML, so notes/apparatus rendered in the page may be mixed into the text.",
    ])
print(rep)
