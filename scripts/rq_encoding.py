#!/usr/bin/env python3
"""Recompute the "encoding" field of catalogue entries from the frozen DB.

Aggregates fmt_detected over each entry's collections (canonical families via
scripts/rq_families.json, individual collections via their slugified name) and
sets the entry's primary encoding with the precedence TEI > XML > HTML >
wikitext > plain-text. Run whenever encoding categories change upstream.

Usage:
    python scripts/rq_encoding.py --db corpus.sqlite
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

FMT_MAP = {
    "tei": "tei",
    "xml": "xml",
    "html": "html",
    "wiki": "wikitext",
    "wikitext": "wikitext",
    "plain": "plain-text",
    "txt": "plain-text",
    "md": "markdown",
}
PRECEDENCE = ["tei", "xml", "html", "wikitext", "plain-text", "markdown"]

# fmt_detected labels plain TEI-XML files as "xml" (extension heuristic). For
# entries where the TEI nature is verified at the source (file sampled or
# project documentation, see git history), force the finer value.
OVERRIDES = {
    # TEI.2/P4 DTD (tei-c.org) sampled in PerseusDL/canonical-engLit 2026-10-08
    "perseus-digital-library": "tei",
    # project docs / notes: "XML-TEI encoding" (polemos), "XML-TEI files"
    # (Mambrino, Zenodo 14235252), "TEI-XML corpus" (Coqalane), TEI editions
    # (Emothe, QhoD, Amadis-in-Translation)
    "polemicagongorina-obvil": "tei",
    "mambrino": "tei",
    "coqalane": "tei",
    "emothe": "tei",
    "qhod": "tei",
    "amadiscorpus-gh": "tei",
    # Well-documented published formats (common knowledge, project docs),
    # where the RQ snapshot ingested a plain-text derivation:
    "dta": "tei",           # DTA publishes TEI P5 (dta.korpusapi / DTAQ)
    "camena": "tei",        # CAMENA editions are TEI P5
    "celt": "tei",          # CELT texts are TEI-conformant SGML / TEI-encoded
    "evans-tcp": "tei",     # Evans-TCP = TCP conversion, TEI P4 XML
    "dbnl": "html",         # DBnL editions are HTML pages
    # mARkdown (OpenITI's own Markdown dialect, .txt files)
    "openiti": "markdown",
}

# Previously verified as TEI (fmt_detected tei at import, or TEI confirmed
# at the source during identification): kept "tei" even where the RQ snapshot
# ingested a plain-text derivation, since encoding describes the edition.
TEI_VERIFIED = [
    "abacus-baroque", "amadiscorpus-gh", "biblioteca-italiana", "bullinger-digital",
    "cavriana-correspondence", "cidtc", "codiaje-judeospanish", "corpus17-french",
    "czech-tei2019", "devonshire-manuscript", "dibilit-german", "dibiphil-renaissance",
    "disco-spanishsonnets", "dracor", "dsl-henriksmith", "dsl-salmer",
    "earlymoderngreek-clarinel", "eebo-text-creation-partnership", "elan-crenum",
    "elan-fnvr", "elan-polygrenaille", "emmo-folger", "ethicacomplementoria",
    "fabulasmitologicas", "fallofconstantinople-arranz", "freem",
    "fuerstinnenkorrespondenz", "gemi-midwifery", "germanc", "gongora-soledades",
    "gongoraobra-obvil", "humanumgitlab", "imp-slovene", "korba-polish",
    "lampeter-english", "mambrino", "map-of-early-modern-london", "mercuregalant",
    "mercurius-baumbank", "obvil-french", "obvil-hainetheatre",
    "polemicagongorina-obvil", "porzio-congiurabaroni", "qhod", "renlowgerman",
    "rin-conde", "rup-folger", "sloveneimp", "sonetossiglodeoro", "ssrq-swisslaw",
    "tbso-gh", "textgrid-repository", "translatoscope-neolat", "welshhcwl",
    "win-lowgermanincunabula", "wolfenbuettelpostil-lithuanian",
    "women-writers-online",
]


def best(fmts: set[str]) -> str:
    codes = {FMT_MAP.get(f, "other") for f in fmts}
    for code in PRECEDENCE:
        if code in codes:
            return code
    return "other"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--families", type=Path, default=REPO_ROOT / "scripts" / "rq_families.json")
    parser.add_argument("--entries-dir", type=Path, default=REPO_ROOT / "data" / "entries")
    args = parser.parse_args()

    fams = json.load(open(args.families))
    groups = fams["groups"]

    con = sqlite3.connect(args.db)
    per_slug: dict[str, set[str]] = {}
    slug_fmts: dict[str, set[str]] = {}
    for collection, fmt in con.execute(
        "SELECT collection, fmt_detected FROM texts WHERE in_core=1 AND is_dup=0"
    ):
        if fmt is None:
            continue
        slug = None
        for g in groups:
            if any(re.search(p, collection) for p in g.get("match", [])):
                slug = g["slug"]
                break
        slug = slug or re.sub(r"[^a-z0-9]+", "-", collection.lower()).strip("-")
        slug_fmts.setdefault(slug, set()).add(fmt)
    con.close()

    changed = 0
    for slug, fmts in slug_fmts.items():
        path = args.entries_dir / f"{slug}.json"
        if not path.exists():
            continue
        entry = json.load(open(path))
        enc = (OVERRIDES.get(slug)
               or ("tei" if slug in TEI_VERIFIED else None)
               or best(fmts))
        if entry.get("encoding") != enc:
            entry["encoding"] = enc
            path.write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
            changed += 1
    print(f"encoding recomputed: {changed} entries changed "
          f"(precedence: {' > '.join(PRECEDENCE)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())