"""Shared helpers for Wolfenbuettel Digital Library editions (diglib.hab.de/edoc/edNNNNNN).

These editions share a layout: <ed>/mets.xml lists the files (xlink:href), transcriptions are TEI P5
files, often with DOCTYPE entity declarations pointing at register files (never resolved here).

Typical use in a per-resource script:
    sys.path[:0] = [HARVEST_DIR, HARVEST_DIR + "/scripts"]
    from hlib import Harvest
    import hab
    h = Harvest("some-id")
    files = hab.mets_files(h, "ed000213", prefix="briefe/")
    data = hab.fetch(h, "ed000213", "briefe/171224.xml", problems)   # bytes or None
    root = hab.parse(data)
    hab.normalise(root)                      # keep original spelling, drop variants/regularisations
    raw = hab.serialise(root)                # str, entity refs removed
"""
from __future__ import annotations

import html
import re
import sys

import requests
from lxml import etree

HAB = "http://diglib.hab.de/edoc/"
TEI = "http://www.tei-c.org/ns/1.0"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"

LANG_NAMES = {
    "deu": "German", "de": "German", "ger": "German", "gmh": "German", "goh": "German",
    "nds": "Low German", "nld": "Dutch", "nl": "Dutch", "dut": "Dutch", "fra": "French", "fr": "French",
    "fre": "French", "lat": "Latin", "la": "Latin", "ita": "Italian", "it": "Italian", "eng": "English",
    "en": "English", "spa": "Spanish", "es": "Spanish", "grc": "Greek", "gre": "Greek", "el": "Greek",
    "por": "Portuguese", "pt": "Portuguese", "heb": "Hebrew",
}


def ln(el) -> str:
    return etree.QName(el).localname if isinstance(el.tag, str) else ""


def mets_files(h, ed: str, prefix: str | None = None, suffix: str = ".xml") -> list[str]:
    """Relative paths listed in <ed>/mets.xml (xlink:href), in order, de-duplicated."""
    txt = h.get(f"{HAB}{ed}/mets.xml", "files/mets.xml")
    out, seen = [], set()
    for m in re.finditer(r'xlink:href="([^"]+)"', txt):
        p = html.unescape(m.group(1)).strip()
        if p.startswith("http") or not p.endswith(suffix) or p in seen:
            continue
        if prefix and not p.startswith(prefix):
            continue
        seen.add(p)
        out.append(p)
    return out


def fetch(h, ed: str, path: str, problems: list | None = None):
    """Fetch <ed>/<path> as bytes (cached under files/<path>); None (and a problem note) on failure."""
    try:
        data = h.get(f"{HAB}{ed}/{path}", f"files/{path}", binary=True)
    except requests.RequestException as e:
        if problems is not None:
            problems.append(f"{path}: {e.__class__.__name__} {str(e)[:80]}")
        return None
    if data[:200].lstrip().lower().startswith((b"<!doctype html", b"<html")):
        if problems is not None:
            problems.append(f"{path}: HTML error page instead of XML")
        return None
    return data


def parse(data: bytes):
    p = etree.XMLParser(recover=True, resolve_entities=False, huge_tree=True, no_network=True)
    return etree.fromstring(data, parser=p)


def _remove(el):
    """Remove el but keep its tail text."""
    par = el.getparent()
    if par is None:
        return
    tail = el.tail
    if tail:
        prev = el.getprevious()
        if prev is not None:
            prev.tail = (prev.tail or "") + tail
        else:
            par.text = (par.text or "") + tail
    par.remove(el)


def _unwrap(el):
    """Replace el by its own content (text and children)."""
    par = el.getparent()
    idx = par.index(el)
    prev = el.getprevious()
    lead = el.text or ""
    if lead:
        if prev is not None:
            prev.tail = (prev.tail or "") + lead
        else:
            par.text = (par.text or "") + lead
    kids = list(el)
    for k in kids:
        par.insert(idx, k)
        idx += 1
    tail = el.tail or ""
    if tail:
        last = kids[-1] if kids else prev
        if last is not None:
            last.tail = (last.tail or "") + tail
        else:
            par.text = (par.text or "") + tail
    par.remove(el)


INLINE = {"choice", "orig", "abbr", "sic", "corr", "ex", "expan", "supplied", "unclear", "hi", "emph", "add",
          "w", "pc", "g", "am", "rs", "term", "name", "persName", "placeName", "date", "foreign", "seg",
          "subst", "num", "measure", "orgName", "geogName"}


def merge_inline(root):
    """Unwrap inline markup so that RQ's counter (which joins every text node with a space) does not
    split words at markup boundaries; drop line/page breaks marked break="no" (hyphenated words)."""
    for el in list(root.iter("{*}lb", "{*}cb", "{*}pb")):
        if el.get("break") == "no":
            _remove(el)
    for el in list(root.iter()):
        if isinstance(el.tag, str) and ln(el) in INLINE and el.getparent() is not None:
            _unwrap(el)
    return root


# elements that RQ's counter drops. lxml's remove() also deletes the tail text, so every dropped element
# silently eats the words that follow it; we therefore remove them ourselves, keeping the tail.
COUNTER_DROP = {"note", "app", "fw", "figDesc", "bibl", "back", "front", "speaker", "label", "ref", "gloss",
                "index", "milestone"}


def strip_editorial(root):
    t = text_el(root)
    if t is None:
        return root
    for el in list(t.iter()):
        if isinstance(el.tag, str) and ln(el) in COUNTER_DROP and el is not t and el.getparent() is not None:
            _remove(el)
    return root


def normalise(root, *, drop_del=True, bibl_to_seg=False, front_back_to_div=False, merge=True):
    """Keep the original-spelling reading and the main text; drop variants and regularisations.

    - entity references (register includes) removed
    - <app>: keep <lem> content only (apparatus readings <rdg> dropped)
    - <reg> dropped (orig/abbr/sic kept); <corr> dropped when paired with <sic>; <expan> dropped when paired with <abbr>
    - <del> dropped (deleted words)
    - optional: <bibl> renamed to <seg> (the counter drops <bibl>), <front>/<back> renamed to <div>
    """
    for e in list(root.iter(etree.Entity)):
        _remove(e)
    for rdg in list(root.iter("{*}rdg")):
        _remove(rdg)
    for app in list(root.iter("{*}app")):
        lem = app.find("{*}lem")
        if lem is not None:
            for k in list(app):
                if k is not lem:
                    _remove(k)
            _unwrap(lem)
            _unwrap(app)
        else:
            _remove(app)
    for el in list(root.iter("{*}reg")):
        _remove(el)
    for el in list(root.iter("{*}corr")):
        par = el.getparent()
        if par is not None and par.find("{*}sic") is not None:
            _remove(el)
    for el in list(root.iter("{*}expan")):
        par = el.getparent()
        if par is not None and par.find("{*}abbr") is not None:
            _remove(el)
    if drop_del:
        for el in list(root.iter("{*}del")):
            _remove(el)
    if bibl_to_seg:
        for el in root.iter("{*}bibl"):
            el.tag = f"{{{TEI}}}seg"
    if front_back_to_div:
        for t in ("front", "back"):
            for el in root.iter(f"{{*}}{t}"):
                el.tag = f"{{{TEI}}}div"
    if merge:
        merge_inline(root)
    strip_editorial(root)
    return root


def serialise(root) -> str:
    return etree.tostring(root, encoding="unicode")


def text_el(root):
    r = root.find(".//{*}text")
    return r


def body_el(root):
    return root.find(".//{*}text/{*}body")


def combine(roots, *, year: int | None = None, title: str = "") -> str:
    """One synthetic TEI document holding the <text> content of several part files."""
    tei = etree.Element(f"{{{TEI}}}TEI", nsmap={None: TEI})
    hdr = etree.SubElement(tei, f"{{{TEI}}}teiHeader")
    fd = etree.SubElement(hdr, f"{{{TEI}}}fileDesc")
    ts = etree.SubElement(fd, f"{{{TEI}}}titleStmt")
    etree.SubElement(ts, f"{{{TEI}}}title").text = title
    if year:
        sd = etree.SubElement(fd, f"{{{TEI}}}sourceDesc")
        etree.SubElement(sd, f"{{{TEI}}}date", when=str(year))
    text = etree.SubElement(tei, f"{{{TEI}}}text")
    body = etree.SubElement(text, f"{{{TEI}}}body")
    for r in roots:
        t = text_el(r)
        if t is None:
            continue
        div = etree.SubElement(body, f"{{{TEI}}}div")
        for k in list(t):
            div.append(k)
    return serialise(tei)


def title_of(root) -> str:
    t = root.find(".//{*}teiHeader//{*}titleStmt/{*}title")
    return re.sub(r"\s+", " ", "".join(t.itertext())).strip() if t is not None else ""


def lang_name(code: str | None, default: str = "German") -> str:
    if not code:
        return default
    c = code.strip().lower().split("-")[0]
    return LANG_NAMES.get(c, default)


def dominant_lang(root, default: str | None = None, scope=None) -> str | None:
    """Language with most words, using xml:lang on elements inside <text>; default if none is marked."""
    scope = scope if scope is not None else text_el(root)
    if scope is None:
        return default
    counts: dict[str, int] = {}
    marked = 0

    def words(el):
        skip = {"note", "index", "teiheader", "app", "bibl", "ref"}
        n = len((el.text or "").split())
        for k in el:
            if isinstance(k.tag, str) and ln(k).lower() not in skip:
                n += words(k)
            n += len((k.tail or "").split())
        return n

    def walk(el):
        nonlocal marked
        for k in el:
            if not isinstance(k.tag, str):
                continue
            if ln(k).lower() in ("note", "index", "teiheader"):
                continue
            lg = k.get(XML_LANG)
            if lg and ln(k) in ("div", "body", "p", "text", "ab", "lg", "quote", "foreign", "head", "seg"):
                if ln(k) in ("foreign", "quote"):
                    continue
                counts[lg] = counts.get(lg, 0) + words(k)
                marked += 1
            else:
                walk(k)

    lg0 = scope.get(XML_LANG)
    walk(scope)
    if counts:
        best = max(counts, key=counts.get)
        return lang_name(best, default or best)
    if lg0:
        return lang_name(lg0, default or lg0)
    b = body_el(root)
    if b is not None and b.get(XML_LANG):
        return lang_name(b.get(XML_LANG), default or b.get(XML_LANG))
    return default


_DE = set("und der die das nicht ist zu mit den dem von ein eine auf für dass daß sich auch als wie wir ich er sie es so aber wenn vnd vndt".split())
_LA = set("et in est quod non ad cum ut quae qui sed ab de ex per quam enim esse sunt aut vel autem etiam".split())
_FR = set("le la les et de des du un une que qui est pour dans pas ne sur au aux avec".split())
_NL = set("de het een en van ik is dat niet te met voor op aen ende der den hy zy".split())


def guess_lang(text: str, default: str = "German") -> str:
    toks = re.findall(r"[a-zäöüß]+", text.lower())[:4000]
    sc = {"German": sum(t in _DE for t in toks), "Latin": sum(t in _LA for t in toks),
          "French": sum(t in _FR for t in toks), "Dutch": sum(t in _NL for t in toks)}
    best = max(sc, key=sc.get)
    return best if sc[best] > 0 else default


def plain(el) -> str:
    return " ".join("".join(el.itertext()).split())
