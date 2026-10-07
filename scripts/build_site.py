#!/usr/bin/env python3
"""Build the static site from catalogue entries.

Reads every JSON file in data/entries/, validates it against the schema,
and writes docs/data.json for the public site. Also writes a CSV export
to docs/renascore.csv.

Usage:
    python scripts/build_site.py [--entries-dir DIR] [--out-dir DIR]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "entry.schema.json"


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def load_entries(entries_dir: Path) -> list[tuple[str, dict]]:
    """Load entries. Returns a list of (filename, entry) tuples."""
    entries = []
    for path in sorted(entries_dir.glob("*.json")):
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
            entries.append((path.name, entry))
        except json.JSONDecodeError as e:
            print(f"Warning: {path.name} is not valid JSON: {e}", file=sys.stderr)
    return entries


def validate_entries(entries: list[tuple[str, dict]], schema: dict) -> list[str]:
    """Validate entries against the schema. Returns a list of error messages."""
    try:
        import jsonschema
    except ImportError:
        print("Warning: jsonschema not installed; skipping validation", file=sys.stderr)
        return []

    errors = []
    validator = jsonschema.Draft7Validator(schema)
    for filename, entry in entries:
        for error in validator.iter_errors(entry):
            path = "/".join(str(p) for p in error.absolute_path) or "(root)"
            errors.append(f"{filename}: {path}: {error.message}")
    return errors


def write_json(entries: list[tuple[str, dict]], out_path: Path) -> None:
    clean = [entry for _, entry in entries]
    payload = {
        "meta": {
            "title": "Renascore",
            "description": "An open catalogue of digital editions of Renaissance-era written documents",
            "licence": "CC0 1.0",
            "source": "https://github.com/Pantagrueliste/renascore",
            "entries": len(clean),
        },
        "entries": clean,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(entries: list[tuple[str, dict]], out_path: Path) -> None:
    cols = [
        "title", "url", "languages", "encoding", "status", "institution",
        "period", "words", "region", "author", "date", "years_active",
        "provenance", "date_added",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for _, entry in entries:
            row = dict(entry)
            if isinstance(row.get("languages"), list):
                row["languages"] = "; ".join(row["languages"])
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entries-dir", type=Path, default=REPO_ROOT / "data" / "entries")
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "docs")
    args = parser.parse_args()

    schema = load_schema()
    entries = load_entries(args.entries_dir)

    if not entries:
        print("Warning: no entries found", file=sys.stderr)

    errors = validate_entries(entries, schema)
    if errors:
        print("Validation errors:", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_json(entries, args.out_dir / "data.json")
    write_csv(entries, args.out_dir / "renascore.csv")

    print(f"Built site: {len(entries)} entries -> {args.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
