#!/usr/bin/env python3
"""Validate a single catalogue entry against the JSON Schema.

Usage:
    python scripts/validate_entry.py data/entries/your-file.json
    python scripts/validate_entry.py data/entries/your-file.json --check-url

Exit code 0 = valid, 1 = invalid.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "entry.schema.json"


def validate_schema(entry: dict, schema: dict) -> list[str]:
    """Return a list of schema validation errors."""
    try:
        import jsonschema
    except ImportError:
        print("Error: jsonschema is not installed. Run: pip install jsonschema", file=sys.stderr)
        sys.exit(2)

    validator = jsonschema.Draft7Validator(schema)
    errors = []
    for error in validator.iter_errors(entry):
        path = "/".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(f"{path}: {error.message}")
    return errors


def check_url(url: str, timeout: float = 10.0) -> tuple[bool, str]:
    """Check that a URL resolves. Returns (ok, message)."""
    try:
        import requests
    except ImportError:
        return True, "requests not installed; skipping URL check"

    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True,
                                 headers={"User-Agent": "RenascoreBot/1.0"})
        if response.status_code >= 400:
            # Some servers reject HEAD; try GET.
            response = requests.get(url, timeout=timeout, allow_redirects=True,
                                    headers={"User-Agent": "RenascoreBot/1.0"},
                                    stream=True)
            response.close()
        if response.status_code >= 400:
            return False, f"HTTP {response.status_code}"
        return True, f"HTTP {response.status_code}"
    except requests.RequestException as e:
        return False, str(e)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entry_file", type=Path, help="Path to the entry JSON file")
    parser.add_argument("--check-url", action="store_true",
                        help="Also check that the URL resolves (requires network)")
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH,
                        help="Path to the schema file")
    args = parser.parse_args()

    if not args.entry_file.exists():
        print(f"Error: file not found: {args.entry_file}", file=sys.stderr)
        return 1

    try:
        entry = json.loads(args.entry_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON: {e}", file=sys.stderr)
        return 1

    schema = json.loads(args.schema.read_text(encoding="utf-8"))

    errors = validate_schema(entry, schema)
    if errors:
        print(f"Schema validation failed for {args.entry_file.name}:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"Schema OK: {args.entry_file.name}")

    if args.check_url:
        url = entry.get("url", "")
        ok, message = check_url(url)
        if ok:
            print(f"URL OK: {url} ({message})")
        else:
            print(f"URL check failed: {url} ({message})")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
