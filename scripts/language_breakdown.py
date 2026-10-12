#!/usr/bin/env python3
"""Record how many texts and words each language contributes to a multilingual entry.

Reads the frozen corpus database (read-only), groups its collections into entries as
rq_statistics does, and writes `language_counts` into every entry with two or more
languages. A language with three texts or fewer also lists those texts by name
(scripts/isolated_titles.json), so a reader knows what to look for on the site.

Usage: python3 scripts/language_breakdown.py --db corpus_master.sqlite
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

try:
    from .languages import catalogue_languages
    from .rq_statistics import project_collections
except ImportError:
    from languages import catalogue_languages
    from rq_statistics import project_collections

ROOT = Path(__file__).resolve().parents[1]
ISOLATED = 3


def breakdown(db: Path) -> dict:
    con = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    rows = con.execute("SELECT collection, lang_display, filename, wordcount FROM texts WHERE in_core = 1").fetchall()
    con.close()
    families = json.loads((ROOT / "scripts/rq_families.json").read_text())
    projects = project_collections({c: {} for c in {r[0] for r in rows}}, families)
    entry_of = {c: e for e, cs in projects.items() for c in cs}
    out: dict = {}
    for coll, lang, filename, words in rows:
        entry = entry_of.get(coll)
        if not entry:
            continue
        label = next(iter(sorted(catalogue_languages([lang]))), lang)
        d = out.setdefault(entry, {}).setdefault(label, {"texts": 0, "words": 0, "files": []})
        d["texts"] += 1
        d["words"] += words or 0
        if filename not in d["files"]:
            d["files"].append(filename)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", required=True, type=Path)
    args = ap.parse_args()
    titles = json.loads((ROOT / "scripts/isolated_titles.json").read_text())
    data, changed = breakdown(args.db), 0
    for path in sorted((ROOT / "data/entries").glob("*.json")):
        langs = data.get(path.stem)
        entry = json.loads(path.read_text())
        before = entry.get("language_counts")
        if not langs or len(langs) < 2:
            entry.pop("language_counts", None)
        else:
            counts = []
            for lang, d in sorted(langs.items(), key=lambda kv: (-kv[1]["words"], kv[0])):
                item = {"language": lang, "texts": d["texts"], "words": d["words"]}
                if d["texts"] <= ISOLATED:
                    item["works"] = [titles[f] for f in d["files"] if f in titles] or None
                    if item["works"] is None:
                        del item["works"]
                counts.append(item)
            entry["language_counts"] = counts
        if entry.get("language_counts") != before:
            path.write_text(json.dumps(entry, ensure_ascii=False, indent=2) + "\n")
            changed += 1
    print(f"{changed} entries updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
