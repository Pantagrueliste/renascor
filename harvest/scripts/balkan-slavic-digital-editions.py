import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys; sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest
import json, re
h = Harvest("balkan-slavic-digital-editions")
B = "https://www.punco.slavistik.lmu.de/"
CS, BG = "Church Slavonic", "Bulgarian"
# (corpus, src): (year, dateless_in_window, language, label, note)
M = {
 # lt = Excerpts
 ("lt","doi"): (1784,0,BG,"Doino Gramatik, Introduction to Paisius (NBKM 370), Elena 1784"),
 ("lt","pcr"): (1793,0,BG,"Petar Carski, NBKM 1423, Plovdiv 1793"),
 ("lt","rai"): (1860,0,BG,"Raikovo damaskin (NBIV 600), 1860"),
 ("lt","brd"): (1749,0,BG,"Josif Bradati, NBKM 328, Samokov 1749"),
 ("lt","pop"): (1821,0,BG,"Pavle Popovic, NBKM 1081, 1821"),
 ("lt","72i"): (1850,0,BG,"Folk damaskin NBKM 722, Job the Rich Man, 19th c. (year approximate)"),
 ("lt","koz"): (1531,0,CS,"Simun Kozicic, Life of St Peter, Rijeka 1531"),
 ("lt","kvd"): (1575,0,CS,"Kiev damaskin, Life of St Mary of Egypt, 1570s-1580s (year approximate)"),
 ("lt","svd"): (1753,0,BG,"Svistov damaskin, Life of St Mary of Egypt, 1753"),
 ("lt","krc"): (1814,0,BG,"Joakim Krcovski, Budapest 1814"),
 ("lt","knd"): (1650,0,BG,"Tixonravov damaskin, Kozma and Damian, 1650-1670s (year approximate)"),
 ("lt","nil"): (1755,0,BG,"Jankulov sbornik NBKM 689, 1755"),
 ("lt","tmr"): (1764,0,BG,"Temski rukopis, 1764"),
 ("lt","bel"): (1776,0,BG,"Beljovski damaskin NBKM 1069, 1776-1778"),
 ("lt","sat"): (None,1,CS,"CIAI 1161, How Michael Defeated Satanael, 16th c."),
 ("lt","zis"): (1805,0,BG,"Sofronii Vracanski, Zitie i stradanie gresnago Sofronija, c. 1805"),
 ("lt","vat"): (1350,0,CS,"Legend of Troy, Vat.slav.2, 14th c. (year approximate)"),
 ("lt","vbg"): (1479,0,CS,"Letters of Wallachian princes (three letters, 1456-1481)"),
 ("lt","kvf"): (950,0,CS,"Kiev Folia, 10th c. (year approximate)"),
 ("lt","pss"): (1050,0,CS,"Psalterium Sinaiticum, 11th c. (year approximate)"),
 ("lt","p3m"): (1875,0,"Macedonian","Pulevski, Macedonian text, 19th c. (year approximate)"),
 ("lt","sms"): (1928,0,"Slovak","Sbornik Matice Slovenskej, Tri dcery, 1928"),
 # petka
 ("petka","vuk"): (1536,0,CS,"Vukovic 1536, Life of St Petka"),
 ("petka","tix"): (1650,0,BG,"Tixonravov damaskin, Life of St Petka, 1650-1670s (year approximate)"),
 ("petka","ros"): (1689,0,CS,"Rostovski (Tuptalo), Kniga zitii svetyx, Kiev 1689"),
 ("petka","709"): (None,1,BG,"NBKM 709, Life of St Petka, 17th c."),
 ("petka","lju"): (1690,0,BG,"Ljubljana damaskin, Life of St Petka, 1690-1700s (year approximate)"),
 ("petka","ion"): (1788,0,BG,"BAN 3312, pop Ioann, Vratsa 1788"),
 ("petka","ber"): (1791,0,BG,"Berlin damaskin, Life of St Petka, 1791-1803"),
 ("petka","020"): (1796,0,BG,"Pop Puncov Sbornik ch. 020, Life of St Petka, 1796"),
 ("petka","ned"): (1806,0,BG,"Nedelnik 1806, Life of St Petka"),
 ("petka","52k"): (1813,0,BG,"Siskov damaskin (Plovdiv archive 52K), 1813"),
 ("petka","728"): (1820,0,BG,"NBKM 728, Life of St Petka, after 1817 (year approximate)"),
 ("petka","gen"): (1820,0,BG,"NBKM 1064, Life of St Petka, 1820s"),
 ("petka","xru"): (1856,0,BG,"Nedelnik 1856 (Xrulev), Life of St Petka"),
 ("petka","bar"): (None,1,CS,"BAR Ms.slav 287, Life of St Petka, 16th c."),
 ("petka","caz"): (1643,0,"Romanian","Varlaam, Cazania, Iasi 1643, Life of St Petka"),
 ("petka","zog"): (1390,0,CS,"Zograph Miscellany (Zogr. 107), Life of St Petka, late 14th c. (year approximate)"),
 # sva
 ("sva","667"): (None,0,CS,"Tale of Alexander the Elder, Veles edition (NBKM 667), 15th c."),
 ("sva","112"): (None,0,CS,"Tale of Alexander the Elder, Odessa edition (1/112), date not given on the site"),
 ("sva","116"): (None,1,CS,"Tale of Alexander the Elder, Sofia edition (CIAI 1161), 16th c."),
 ("sva","ran"): (None,0,CS,"Tale of Alexander the Elder, Petersburg edition, date not given on the site"),
 ("sva","326"): (1750,0,CS,"Tale of Alexander the Elder, Adzar edition (NBKM 326), 18th c. (year approximate)"),
}
files = {"lt": ["lt_data.json"], "petka": ["petka_data.json"], "sva": ["sva_data.json"], "punco": ["data_1.json", "data_2.json"]}
probs = []
SYM = re.compile(r"^[\W_]*$")
def build(sent):
    out, cur, lines = [], None, []
    for tid, t in sent.items():
        w = t["dipl"].strip()
        if not w or SYM.match(w) and w not in ("-",):  # editorial symbols (===, club, dagger)
            continue
        if t["sent"] != cur:
            if lines: out.append(" ".join(lines)); lines = []
            cur = t["sent"]
        lines.append(w)
    if lines: out.append(" ".join(lines))
    return "\n".join(out)
acc = {}
for corpus, fl in files.items():
    for fn in fl:
        d = json.loads(h.get(B + fn, f"files/{fn}"))
        for key, sent in d.items():
            toks = list(sent.values())
            src = toks[0].get("src")
            desc = next((t["src_desc"] for t in toks if t.get("src_desc")), None)
            if corpus == "punco":
                year, dl, lang, label = 1796, 0, BG, f"Pop Puncov Sbornik (NBKM 693), chapter {src}: {desc}"
            else:
                if src is None and corpus == "petka": src = "zog"
                year, dl, lang, label = M[(corpus, src)]
            text = build(sent)
            k = (corpus, src)
            if k in acc:
                acc[k][0] += "\n" + text
                probs.append(f"{corpus}-{src}: several data blocks merged into one text")
            else:
                acc[k] = [text, year, dl, lang, label]
for (corpus, src), (text, year, dl, lang, label) in acc.items():
    h.add(f"{corpus}-{src}.txt", text, language=lang, year=year, dateless_in_window=bool(dl),
          source=f"Balkan Slavic Digital Editions: {label}", url=B + ("search_engine.php?corpus=" + corpus if corpus != "punco" else "search_engine.php"))
probs += [
 "Texts rebuilt from the portal's own token-level JSON files (lt_data.json, petka_data.json, sva_data.json, data_1/2.json, linked from search_engine.php); diplomatic Latin transliteration column 'dipl' only (Cyrillic, lemmas, tags, English translations dropped). Editorial symbols alone as tokens (===, club, dagger) removed; critical-edition markers like [...] and *folio* numbers remain inside the text.",
 "Dates are not in the data files: taken from the site's description pages and CLARIN.SI deposit 11356/1441 headers; those marked 'approximate' in the source field are estimates (century midpoints or decades). Texts known only by century that lies wholly in 1450-1700 (16th/17th c.) are year=None with dateless_in_window=True: Sofia Alexander edition, CIAI 1161 Satanael text, NBKM 709, BAR Ms.slav 287. Veles (15th c.), Odessa and Petersburg Alexander editions have no year on the site (undated, not counted in window).",
 "Letters of Wallachian princes are three letters (1456-1481) in one record (the data has no letter boundary), year 1479.",
 "Joseph-Volokolamsk 1537 manuscript is mentioned on the site but has no text in the data files; not harvested. Excerpts and Petka sources of 1450-1700 present: Vukovic 1536, Kozicic 1531, Letters, Rostovski 1689, Varlaam 1643, Tixonravov, Ljubljana, Kiev damaskin.",
 "Same texts partly overlap the CLARIN.SI deposit 11356/1441 (23 texts), which was not harvested separately to avoid duplicates. License CC BY-SA 4.0 (site).",
]
rep = h.finish(method="Found the portal's data JSON files by reading search_engine.php; downloaded 6 JSON files (lt, petka, sva, data_1, data_2) and rebuilt each text from the 'dipl' tokens.",
  coverage="All texts in the portal's corpora (Excerpts 22, Life of St Petka 16, Tale of Alexander 5, Pop Puncov Sbornik 85 chapters); only part falls within 1450-1700 (the Sbornik, 1796, is entirely outside).", problems=probs)
print(rep["texts_total"], rep["texts_in_window"], rep["words_in_window"], rep["undated"], rep["language_words"])
