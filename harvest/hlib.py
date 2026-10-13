"""Shared helpers for the Renascor 2026-10 harvest.

Each resource is harvested into RQ/data/raw/renascor_2026-10/<id>/:
  files/          downloaded source files (as fetched)
  staging.jsonl   one record per text, in the RQ ingest format
  report.json     what was done, written by finish()

Usage in a harvest script:
    import sys; sys.path.insert(0, HARVEST_DIR)
    from hlib import Harvest
    h = Harvest("hartlib-papers")
    raw = h.get("https://...", "files/x.xml")        # cached, polite fetch
    h.add("x.xml", raw, language="English", year=1650, source="Hartlib Papers")
    h.finish(method="...", coverage="...", problems=[...])
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

import requests

import os as _os
RQ = Path(_os.environ.get("RQ_ROOT", Path(__file__).resolve().parents[2] / "RQ"))
sys.path.insert(0, str(RQ / "src"))
from rqfootprint.textstats import stats  # noqa: E402

OUT = RQ / "data" / "raw" / "renascor_2026-10"
UA = "Renascor-harvest/0.1 (+https://pantagrueliste.github.io/renascor/)"
LO, HI = 1450, 1700
_YEAR = re.compile(r"(?<!\d)(1[3-9]\d\d)(?!\d)")


def first_year(s: str | None) -> int | None:
    """First plausible four-digit year (1300-1999) in a date string such as '1563-04-02' or 'c. 1590'."""
    if not s:
        return None
    m = _YEAR.search(str(s))
    return int(m.group(1)) if m else None


def tei_year(xml: str) -> int | None:
    """Best-effort date of the source (not of the digital file) from a TEI header."""
    for pat in (
        r"<sourceDesc\b.*?</sourceDesc>",
        r"<profileDesc\b.*?</profileDesc>",
        r"<correspAction\b[^>]*type=\"sent\".*?</correspAction>",
    ):
        m = re.search(pat, xml, re.S)
        if not m:
            continue
        block = m.group(0)
        d = re.search(r"<date\b[^>]*\b(?:when|notBefore|from)=\"([^\"]+)\"", block)
        if d and first_year(d.group(1)):
            return first_year(d.group(1))
        d = re.search(r"<date\b[^>]*>(.*?)</date>", block, re.S)
        if d and first_year(re.sub(r"<[^>]+>", "", d.group(1))):
            return first_year(re.sub(r"<[^>]+>", "", d.group(1)))
    return None


class Harvest:
    def __init__(self, rid: str, delay: float = 1.0):
        self.id = rid
        self.dir = OUT / rid
        (self.dir / "files").mkdir(parents=True, exist_ok=True)
        self.delay = delay
        self.s = requests.Session()
        self.s.headers["User-Agent"] = UA
        self.records: list[dict] = []
        self.seen: set[str] = set()
        self._last = 0.0

    def get(self, url: str, rel: str | None = None, binary: bool = False, **kw):
        """Fetch url politely (delay between requests); cache to files/ when rel is given."""
        if rel:
            p = self.dir / rel
            if p.exists():
                return p.read_bytes() if binary else p.read_text(encoding="utf-8", errors="replace")
        wait = self.delay - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        r = self.s.get(url, timeout=60, **kw)
        self._last = time.time()
        r.raise_for_status()
        if binary:
            data = r.content
        else:
            r.encoding = r.encoding if r.encoding and r.encoding.lower() != "iso-8859-1" else r.apparent_encoding
            data = r.text
        if rel:
            p = self.dir / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            (p.write_bytes(data) if binary else p.write_text(data, encoding="utf-8"))
        return data

    def add(self, filename: str, raw: str, *, language: str, year: int | None,
            source: str, url: str = "", dateless_in_window: bool = False, **extra):
        """Record one text. Out-of-window years are kept in staging but flagged (ingest sets in_core=0)."""
        if filename in self.seen:
            raise ValueError(f"duplicate filename {filename}")
        self.seen.add(filename)
        rec = {"collection": f"Renascor_{self.id}", "filename": filename, "raw": raw,
               "language": language, "year": year, "source": source, "origin": url or source,
               "dateless_in_window": bool(dateless_in_window and year is None)}
        rec.update(extra)
        self.records.append(rec)

    def finish(self, *, method: str, coverage: str, problems: list[str] | None = None):
        with open(self.dir / "staging.jsonl", "w", encoding="utf-8") as fh:
            for r in self.records:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        n = w = n_in = w_in = undated = 0
        langs: dict[str, int] = {}
        for r in self.records:
            st = stats(r["raw"])
            n += 1
            w += st["words"]
            y = r["year"]
            inside = (y is not None and LO <= y <= HI) or (y is None and r["dateless_in_window"])
            undated += y is None
            if inside:
                n_in += 1
                w_in += st["words"]
                langs[r["language"]] = langs.get(r["language"], 0) + st["words"]
        rep = {"id": self.id, "texts_total": n, "words_total": w, "texts_in_window": n_in,
               "words_in_window": w_in, "undated": undated, "language_words": langs,
               "method": method, "coverage": coverage, "problems": problems or []}
        (self.dir / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
        return rep


def slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", urllib.parse.unquote(s)).strip("_")[:150]
