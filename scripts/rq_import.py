#!/usr/bin/env python3
"""Import RQ Open Corpus collections into Renascor entries.

Reads the frozen RQ corpus metadata database (SQLite), groups its
collections into canonical edition projects via scripts/rq_families.json
(one entry per documented project, all languages merged), and writes one
JSON entry per canonical project into data/entries/.

Collections that match no documented project (micro-collections, generic
platforms, unidentifiable origins) are imported individually from the RQ
source inventory: each gets its own entry, with the first working URL from
its source_ref column, or a pointer to the RQ Open Corpus frozen release
when nothing verifiable resolves. A pending report lists the rare
collections that could not be imported at all.

Usage:
    python scripts/rq_import.py --db sqlite.db [--families FILE]
                                [--inventory FILE] [--out-dir DIR]
                                [--report FILE]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import sys
import urllib.request
import urllib.error
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FAMILIES_PATH = REPO_ROOT / "scripts" / "rq_families.json"

STATS_NOTE = (
    "Corpus statistics (text, word and language counts, period) derived "
    "from the RQ Open Corpus snapshot v2026.06 (in-core, deduplicated texts)."
)

FALLBACK_URL = "https://github.com/Pantagrueliste/rq-open-corpus/releases/tag/v2026.06-frozen"

USER_AGENT = "Mozilla/5.0 (compatible; renascor-link-checker/1.0)"


def url_ok(url: str, timeout: float = 15.0) -> bool:
    """True if the URL answers (403 counts as reachable: many sites block bots)."""
    req = urllib.request.Request(url, method="HEAD",
                                 headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except urllib.error.HTTPError as e:
        return e.code != 404
    except Exception:
        return False


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def canonical_for(collection: str, groups: list[dict]) -> dict | None:
    for g in groups:
        for pattern in g.get("match", []):
            if re.search(pattern, collection):
                return g
    return None


def aggregate(db_path: Path, collections: list[str]) -> dict:
    """Aggregate in-core, deduplicated texts over a set of RQ collections."""
    con = sqlite3.connect(db_path)
    placeholders = ",".join("?" * len(collections))
    rows = con.execute(
        f"SELECT lang_display, year, wordcount, fmt_detected, origin FROM texts "
        f"WHERE in_core=1 AND is_dup=0 AND collection IN ({placeholders})",
        collections,
    ).fetchall()
    con.close()
    langs, fmts, origins, years, words = set(), set(), [], [], 0
    for lang, year, wordcount, fmt, origin in rows:
        if lang:
            langs.add(lang)
        if year:
            years.append(int(year))
        if isinstance(wordcount, int):
            words += wordcount
        if fmt:
            fmts.add(fmt)
        if origin:
            origins.append(origin)
    return {"langs": langs, "fmts": fmts, "origins": origins,
            "period": (min(years), max(years)) if years else None,
            "words": words, "texts": len(rows)}


def build_entry(group: dict, stats: dict, existing: dict | None, today: str,
                merge_stats: bool = True) -> dict:
    entry = dict(existing) if existing else {}
    if not existing:
        entry["title"] = group["title"]
        entry["url"] = group["url"]
        entry["status"] = "active"
        entry["provenance"] = "submitted"
        entry["date_added"] = today
        if group.get("institution"):
            entry["institution"] = group["institution"]
        if group.get("notes"):
            entry["notes"] = group["notes"]
        if group.get("status"):
            entry["status"] = group["status"]
    entry["languages"] = sorted(
        set(entry.get("languages") or []) | {code for code in stats["langs"] if code}
    )
    if merge_stats:
        # an explicit "encoding" on the family group overrides the fmt-derived one
        entry["encoding"] = group.get("encoding") or primary_encoding(stats["fmts"])
        if stats["words"]:
            entry["words"] = stats["words"]
        entry["texts"] = stats["texts"]
        if stats["period"]:
            lo, hi = stats["period"]
            entry["period"] = f"{lo}-{hi}"
    return entry


FALLBACK_NOTE = (
    "No public project page could be verified for this collection; it is "
    "documented here as a corpus collection of the RQ Open Corpus snapshot "
    "(v2026.06-frozen). The original harvest reference is given below."
)


def inventory_entry(collection: str, inv_row: dict, stats: dict, today: str,
                    known: dict | None = None) -> dict | None:
    """Build a per-collection entry from the RQ source inventory."""
    known = known or {}
    candidates = []
    if known.get("url"):
        candidates.append(known["url"])
    ref_urls = dict.fromkeys(url_re.findall(inv_row["source_ref"]))
    candidates += [u.rstrip("/") for u in ref_urls]
    url = next((u for u in candidates if url_ok(u)), None)
    notes = STATS_NOTE
    if url is None:
        url = known.get("fallback") or FALLBACK_URL
        notes = FALLBACK_NOTE + " " + STATS_NOTE
    title = (inv_row["collection"] or collection).replace("_", " ")
    if not title.strip():
        title = collection
    if known.get("title"):
        title = known["title"]
    entry = {
        "title": title,
        "url": url,
        "languages": sorted(l for l in stats["langs"] if l),
        "encoding": primary_encoding(stats["fmts"]),
        "status": "active",
        "provenance": "submitted",
        "date_added": today,
        "words": stats["words"],
        "texts": stats["texts"],
    }
    if known.get("institution"):
        entry["institution"] = known["institution"]
    if stats["period"]:
        entry["period"] = f"{stats['period'][0]}-{stats['period'][1]}"
    origin_sample = inv_row["source_ref"][:200]
    entry["notes"] = f"{notes} {origin_sample}".strip()
    return entry


FMT_MAP = {"tei": "tei", "xml": "xml", "html": "html", "wiki": "wikitext",
           "wikitext": "wikitext", "plain": "plain-text", "txt": "plain-text",
           "md": "markdown"}
ENCODING_PRECEDENCE = ["tei", "xml", "html", "wikitext", "plain-text", "markdown"]


def primary_encoding(fmts: set) -> str:
    """Primary encoding of a text set, given the RQ fmt_detected values."""
    codes = {FMT_MAP.get(f, "other") for f in fmts}
    return next((c for c in ENCODING_PRECEDENCE if c in codes), "other")


url_re = re.compile(r'https?://[^\s;,"]+')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--families", type=Path, default=FAMILIES_PATH)
    parser.add_argument("--inventory", type=Path, default=None,
                        help="RQ source inventory CSV (verification kit)")
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "data" / "entries")
    parser.add_argument("--report", type=Path,
                        default=REPO_ROOT / "data" / "rq_pending.csv")
    args = parser.parse_args()
    today = date.today().isoformat()

    groups = json.loads(args.families.read_text(encoding="utf-8"))["groups"]
    fams = json.loads(args.families.read_text(encoding="utf-8"))
    groups = fams["groups"]
    known_all = fams.get("known_collections", {})
    con = sqlite3.connect(args.db)
    collections = [r[0] for r in con.execute(
        "SELECT DISTINCT collection FROM texts WHERE in_core=1 AND is_dup=0 ORDER BY collection"
    )]
    con.close()

    excluded = fams.get("exclude", {})
    excluded_out = [c for c in collections if c in excluded]
    collections = [c for c in collections if c not in excluded]

    assigned: dict[str, list[str]] = {}
    pending: list[str] = []
    for c in collections:
        g = canonical_for(c, groups)
        if g:
            assigned.setdefault(g["slug"], []).append(c)
        else:
            pending.append(c)

    # Existing entries for update-in-place.
    written, updated, skipped = [], [], []
    for g in groups:
        slug = g.get("slug")
        members = assigned.get(slug)
        if not members:
            continue
        members = [c for c in members if c not in g.get("drop", [])]
        if not members:
            continue
        stats = aggregate(args.db, members)
        out_path = args.out_dir / f"{slug}.json"
        existing = None
        if out_path.exists():
            try:
                existing = json.loads(out_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing = None
        if not g.get("url"):
            skipped.append(slug)
            continue
        entry = build_entry(g, stats, existing, today,
                            merge_stats=g.get("merge_stats", True))
        out_path.write_text(
            json.dumps(entry, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (written if not existing else updated).append(slug)

    imported_leftovers = []
    inventory = {}
    if args.inventory:
        inventory = {r["collection"]: r for r in
                     csv.DictReader(args.inventory.open(encoding="utf-8"))}
    for c in pending:
        slug = slugify(c)
        path = args.out_dir / f"{slug}.json"
        # Support re-running: an existing entry is "imported" only if it is ours.
        if path.exists():
            try:
                existing_title = json.loads(path.read_text(encoding="utf-8")).get("title", "")
            except Exception:
                existing_title = None
            known_title = (known_all.get(c) or {}).get("title")
            if existing_title is not None and (
                existing_title.replace("_", " ") == c.replace("_", " ")
                or (known_title and existing_title == known_title)
            ):
                imported_leftovers.append(slug)
                continue
            print(f"Warning: {path.name} exists with a different title; not overwriting",
                  file=sys.stderr)
            continue
        stats = aggregate(args.db, [c])
        row = inventory.get(c)
        new_entry = inventory_entry(c, row, stats, today, known_all.get(c)) if row else None
        if new_entry:
            path.write_text(json.dumps(new_entry, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
            imported_leftovers.append(slug)
        else:
            print(f"Still pending (no working URL in source_ref): {c}", file=sys.stderr)

    # Refresh the pending report: keep only collections not written as entries.
    imported_slugs = set(imported_leftovers)
    with args.report.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["collection", "texts", "words", "languages", "period", "origin_sample"])
        con = sqlite3.connect(args.db)
        mapped_collections = {c for members in assigned.values() for c in members}
        still_pending = [c for c in pending if slugify(c) not in imported_slugs]
        for c in still_pending:
            r = con.execute(
                "SELECT COUNT(*), COALESCE(SUM(wordcount),0), "
                "GROUP_CONCAT(DISTINCT lang_display), MIN(year), MAX(year), "
                "COALESCE(MIN(origin),'') FROM texts "
                "WHERE in_core=1 AND is_dup=0 AND collection=?", (c,)
            ).fetchone()
            period = f"{r[3]}-{r[4]}" if r[3] is not None else ""
            w.writerow([c, r[0], r[1], r[2], period, r[5][:120]])
        con.close()

    print(f"Mapped {sum(len(v) for v in assigned.values())} of {len(collections)} "
          f"collections into {len(written) + len(updated)} canonical projects "
          f"({len(updated)} updated, {len(written)} new, {len(skipped)} skipped without URL).")
    for c in excluded_out:
        print(f"  excluded: {c} ({excluded[c]})")
    print(f"Leftover collections imported individually: {len(imported_leftovers)}")
    for slug in written:
        print(f"  new:      {slug}")
    for slug in imported_leftovers:
        print(f"  leftover: {slug}")
    for slug in updated:
        print(f"  updated:  {slug}")
    for slug in skipped:
        print(f"  skipped (no URL): {slug}")
    return 0


if __name__ == "__main__":
    sys.exit(main())