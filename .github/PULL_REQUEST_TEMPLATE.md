## What this PR does

<!-- Briefly describe the change. If you are adding a new entry, say which project. -->

## Checklist

- [ ] I have read [CONTRIBUTING.md](../CONTRIBUTING.md).
- [ ] If adding a new entry: the JSON file is in `data/entries/` and named after the project (lowercase, hyphens, `.json` extension).
- [ ] If adding a new entry: the entry validates against the schema (`python scripts/validate_entry.py data/entries/your-file.json`).
- [ ] If adding a new entry: the URL resolves (checked with `--check-url`).
- [ ] If adding a new entry: I have not duplicated an existing entry (checked the catalogue first).
- [ ] If modifying an existing entry: I have explained what was wrong and why the change is correct.
- [ ] I have run `python scripts/build_site.py` to regenerate `docs/data.json` and `docs/renascor.csv`.

## Notes for the reviewer

<!-- Anything the reviewer should pay attention to? Uncertainty about a field? A borderline scope decision? -->
