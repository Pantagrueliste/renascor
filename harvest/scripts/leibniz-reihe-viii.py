import os as _os
HARVEST_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, re, glob, os, html, collections
sys.path.insert(0, HARVEST_DIR + "")
from hlib import Harvest, first_year
h = Harvest("leibniz-reihe-viii")
F = h.dir / "files"

def get_divs(s, typ):
    """Return inner XML of top-level <div type=typ> blocks (depth aware)."""
    out = []
    for m in re.finditer(r'<div type="%s"[^>]*>' % typ, s):
        i = m.end(); depth = 1
        for t in re.finditer(r"<div\b[^>]*?(/?)>|</div>", s[i:]):
            if t.group(0) == "</div>": depth -= 1
            elif not t.group(1): depth += 1
            if depth == 0:
                out.append(s[i:i + t.start()]); break
    return out

def clean_text(x):
    x = re.sub(r"<note\b[^>]*/>", "", x)
    for _ in range(4):
        x = re.sub(r"<note\b[^>]*>(?:(?!<note\b).)*?</note>", "", x, flags=re.S)
    x = re.sub(r"<rdg\b.*?</rdg>", "", x, flags=re.S)
    x = re.sub(r"<(?:index|formula|fw|figure|graphic|bibl|anchor)\b[^>]*/>", "", x)
    x = re.sub(r"<(index|formula|fw|figure|bibl)\b[^>]*>.*?</\1>", "", x, flags=re.S)
    x = re.sub(r"<pb\b[^>]*/>", " ", x)
    return x

def head_date(s):
    hs = re.findall(r"<head>(.*?)</head>", s, re.S)
    for hd in hs[1:]:
        t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", hd)).strip()
        if len(t) <= 80 and not t.startswith("[Fig") and first_year(t):
            return first_year(t), t
    return None, None

FR = set("le la les des du est une que qui dans pour avec sur par au aux ses son sa leur et en ne pas ce cette sont il on".split())
DE = set("der die das und ist nicht ein eine zu von mit auf den dem des sich auch als wie bei aus wird werden oder".split())
LA = set("et in ad est cum quod non qui ut de sunt per ex sed aut si quae quam esse sit enim vel autem hoc".split())
def lang(txt):
    w = re.findall(r"[a-zäöüßéèàâêîôûç]+", txt.lower())
    sc = {n: sum(x in S for x in w) for n, S in (("French", FR), ("German", DE), ("Latin", LA))}
    return max(sc, key=sc.get)

chapter_date = {}
for f in sorted(glob.glob(str(F / "band0*/tei/Einzeldateien/L_chapter_*.xml"))):
    s = open(f, encoding="utf-8").read()
    chapter_date[f] = head_date(s)

nodate = 0; nodivs = 0; recs = 0
for f in sorted(glob.glob(str(F / "band0*/tei/Einzeldateien/L_*_*.xml"))):
    s = open(f, encoding="utf-8").read()
    band = f.split("/band")[1][:2]
    texts = get_divs(s, "text")
    if not texts:
        nodivs += 1; continue
    y, dstr = head_date(s)
    if y is None:
        m = re.search(r'xml:id="Ch(\d+)\.S\d+"', s)
        if m:
            cf = f.replace(os.path.basename(f), f"L_chapter_{m.group(1)}.xml")
            y, dstr = chapter_date.get(cf, (None, None))
    raw_txt = "\n\n".join(clean_text(t) for t in texts)
    raw = '<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>' + raw_txt + "</body></text></TEI>"
    plain = re.sub(r"<[^>]+>", " ", raw_txt)
    plain = html.unescape(plain)
    if not re.sub(r"\s+", "", plain): continue
    if y is None: nodate += 1
    hd = re.search(r"<head>(.*?)</head>", s, re.S)
    title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", hd.group(1))).strip() if hd else ""
    h.add(f"band{band}_" + os.path.basename(f), raw, language=lang(plain), year=y, source="Leibniz AA VIII, %s: %s" % (int(band), title), url="https://github.com/telota/LeibnizVIII-LaTeX_TEI", date_text=dstr)
    recs += 1
print(h.finish(method="Fetched the TEI Einzeldateien (L_chapter_N / L_section_N, one file per Stück, XInclude-split) of volumes 1-3 from raw.githubusercontent.com; for each Stück only the <div type=text> (Leibniz's text) is kept, with the critical apparatus (rdg), editorial notes, index entries, formulas, folio markers and bibliographic items removed (lemma text kept). Year = first year in the bracketed date line under the Stück's title (for section files, the date of the parent chapter). Language per Stück from stopword counts.",
  coverage="Volumes VIII,1, VIII,2 and VIII,3 (TEI); volume VIII,4 only exists as PDF and was not harvested. All Stücke with an edited text; front matter, introductions, indexes, bibliographies, registers excluded.",
  problems=[f"{nodate} Stücke without a parseable date (year=None, dateless_in_window=False).", f"{nodivs} chapter/section files without a text division (containers or intros) skipped.", "Texts dated after 1700 in vol. 3 (kept in staging with year, counted out). Date ranges taken at their first year. Mixed-language Stücke (Latin with French or German) get one main language; mathematical formulas (MathML) dropped, so words in formula-heavy pieces are understated. Stücke with date straddling 1700 are classed by first year."]))
