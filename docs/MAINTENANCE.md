# Maintaining Renascor

## Build and check

```bash
python3 -m pip install -e .
python3 scripts/build_site.py
python3 -m unittest discover -s tests -v
python3 -m http.server 8000 --directory docs
```

The build validates every entry and generates `docs/data.json`, `docs/renascor.csv` and `docs/renascor.json`. It also updates the figures and charts in `docs/index.html`. Rebuilding unchanged data is deterministic.

For a scratch build:

```bash
python3 scripts/build_site.py --entries-dir /path/to/entries --out-dir /tmp/renascor-site
```

The public data date and commit link come from the most recent commit that changed `data/entries`. After committing entries, rebuild and commit the generated provenance update.

## Collection sizes and corpus contributions

Catalogue `words` and `texts` count resource text instances within 1450–1700 before content deduplication. `corpus_statistics` separately preserves the original Renascor Corpus contribution after its duplicate filter. Partial harvests must be identified; omitted counts mean unknown. Totals across resources include overlaps. The headline corpus total instead sums the complete audit’s deduplicated corpus counts, before grouping collections into catalogue records. It uses the June working snapshot and never adds later resource censuses to that total without corpus deduplication.

The Renascor Corpus is ongoing and unreleased. Historical `rq` script names and paths remain for reproducibility. To refresh figures from the exact frozen June working database, with recovery from checksum-locked staging files:

```bash
python3 scripts/rq_statistics.py --db /path/to/corpus_master_FROZEN_2026-06-26.sqlite --rq-root /path/to/RQ
python3 scripts/build_site.py
```

The recount reads the corpus without changing it and writes its audit to [data/rq_statistics.json](../data/rq_statistics.json). Material excluded before saved harvests remains unknown. Imports use the recount only when its database checksum matches.

## Sefaria source census

```bash
python3 scripts/sefaria_catalogue.py --update-entry
python3 scripts/build_site.py
```

The census uses Sefaria’s API inventory and composition dates from official export indexes, with API fallback. It counts individual Hebrew source editions whose complete recorded composition-date range falls within 1450–1700, including repeated content. Generated merged copies and translations are excluded. Composition dates take precedence over later printing dates.

Downloads are cached locally. Re-running replays the cached sources; add `--refresh` to fetch fresh data. The text-free audit [data/sefaria_statistics.json](../data/sefaria_statistics.json) records retrieval dates, checksums, undated and boundary-crossing works, and works without a counted source edition. The separate June corpus contribution is preserved by later source and corpus refreshes.

## Licences and formats

Each record gives the edition text’s licence, independently of the catalogue metadata’s CC0 licence. Publisher evidence is stored in [scripts/rq_licenses_verified.json](../scripts/rq_licenses_verified.json). Legacy corpus `copyright_status` values are not licence evidence; unestablished rights appear as “Not stated”.

Encoding describes the richest publicly available text format. Internal XML used for search or storage does not establish an XML download. Record multiple downloadable formats in `data_formats` and official API documentation in `api_url`.

## Discovery and funding

The [weekly discovery agent](../agent/README.md) proposes candidates as pull requests for human review. See [CONTRIBUTING.md](../CONTRIBUTING.md) and the [schema guide](../schema/README.md).

[.github/FUNDING.yml](../.github/FUNDING.yml) configures GitHub’s Sponsor button to link to [Ko-fi](https://ko-fi.com/clementgodbarge).
