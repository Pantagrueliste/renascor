#!/usr/bin/env python3
"""Validate all catalogue entries against the JSON Schema.

Usage:
    python scripts/validate_all.py [--entries-dir DIR] [--check-urls]

Exit code 0 = all valid, 1 = validation errors found.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "entry.schema.json"
COUNTRIES_PATH = REPO_ROOT / "schema" / "countries.json"


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def load_entries(entries_dir: Path) -> list[tuple[str, dict]]:
    entries = []
    for path in sorted(entries_dir.glob("*.json")):
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
            entries.append((path.name, entry))
        except json.JSONDecodeError as e:
            print(f"Error: {path.name} is not valid JSON: {e}", file=sys.stderr)
    return entries


def validate_schema(entries: list[tuple[str, dict]], schema: dict) -> list[str]:
    """Validate entries against the schema. Returns error messages."""
    try:
        import jsonschema
    except ImportError:
        print("Error: jsonschema is not installed. Run: pip install jsonschema", file=sys.stderr)
        sys.exit(2)

    errors = []
    validator = jsonschema.Draft7Validator(schema)
    for filename, entry in entries:
        for error in validator.iter_errors(entry):
            path = "/".join(str(p) for p in error.absolute_path) or "(root)"
            errors.append(f"{filename}: {path}: {error.message}")
    return errors


def validate_countries(entries: list[tuple[str, dict]]) -> list[str]:
    """Every country code must be listed in schema/countries.json. Returns error messages."""
    known = json.loads(COUNTRIES_PATH.read_text(encoding="utf-8"))["countries"]
    return [f"{filename}: countries: unknown code {code!r} (add it to schema/countries.json)"
            for filename, entry in entries
            for code in entry.get("countries", []) if code not in known]


def check_urls(entries: list[tuple[str, dict]], timeout: float = 10.0) -> list[str]:
    """Check that entry URLs resolve. Returns warning messages."""
    try:
        import requests
    except ImportError:
        print("Warning: requests not installed; skipping URL checks", file=sys.stderr)
        return []

    warnings = []
    urls = [(filename, url) for filename, entry in entries
            for url in (entry.get("url", ""), entry.get("data_url", "")) if url]
    for filename, url in urls:
        try:
            response = requests.head(url, timeout=timeout, allow_redirects=True,
                                     headers={"User-Agent": "RenascorBot/1.0 (validation)"})
            if response.status_code >= 400:
                # Some servers reject HEAD; try GET.
                response = requests.get(url, timeout=timeout, allow_redirects=True,
                                        headers={"User-Agent": "RenascorBot/1.0 (validation)"},
                                        stream=True)
                response.close()
            if response.status_code >= 400:
                warnings.append(f"{filename}: URL returned HTTP {response.status_code}: {url}")
        except requests.RequestException as e:
            warnings.append(f"{filename}: URL check failed: {url} ({e})")
    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entries-dir", type=Path, default=REPO_ROOT / "data" / "entries")
    parser.add_argument("--check-urls", action="store_true",
                        help="Check that URLs resolve (requires network, slower)")
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    args = parser.parse_args()

    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    entries = load_entries(args.entries_dir)

    if not entries:
        print(f"Error: no entries found in {args.entries_dir}", file=sys.stderr)
        return 1

    print(f"Validating {len(entries)} entries...")

    # Schema validation (fatal).
    errors = validate_schema(entries, schema) + validate_countries(entries)
    if errors:
        print(f"\nSchema validation failed ({len(errors)} errors):")
        for e in errors:
            print(f"  {e}")
        return 1
    print("  Schema: OK")

    # URL checks (warnings only, not fatal).
    if args.check_urls:
        print("  Checking URLs...")
        warnings = check_urls(entries)
        if warnings:
            print(f"\nURL warnings ({len(warnings)}):")
            for w in warnings:
                print(f"  {w}")
        else:
            print("  URLs: OK")

    print(f"\nAll {len(entries)} entries are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
