# Maintaining Renascor

## Build and check

```bash
python3 -m pip install -e .
python3 scripts/build_site.py
python3 -m unittest discover -s tests -v
python3 -m http.server 8000 --directory docs
```

The build validates every entry and generates `docs/data.json`, `docs/renascor.csv`, `docs/renascor.json` and `docs/renascor.bib`. It also updates the figures and charts in `docs/index.html`. Rebuilding unchanged data is deterministic.

For a scratch build:

```bash
python3 scripts/build_site.py --entries-dir /path/to/entries --out-dir /tmp/renascor-site
```

The public data date and commit link come from the most recent commit that changed `data/entries`. After committing entries, rebuild and commit the generated provenance update.

## Collection sizes and corpus contributions

Catalogue `words` and `texts` count resource text instances within 1450–1700 before content deduplication. `corpus_statistics` separately preserves the original Renascor Corpus contribution after its duplicate filter. Partial harvests must be identified; omitted counts mean unknown. Totals across resources include overlaps. The headline corpus total instead sums the complete audit’s deduplicated corpus counts, before grouping collections into catalogue records. It uses the latest working snapshot and never adds later resource censuses to that total without corpus deduplication.

The Renascor Corpus is ongoing and unreleased. Historical `rq` script names and paths remain for reproducibility. To refresh figures from the exact frozen June working database, with recovery from checksum-locked staging files:

```bash
python3 scripts/rq_statistics.py --db /path/to/corpus_master_FROZEN_2026-06-26.sqlite --rq-root /path/to/RQ
python3 scripts/build_site.py
```

The recount reads the corpus without changing it and writes its audit to [data/rq_statistics.json](../data/rq_statistics.json). Material excluded before saved harvests remains unknown. Imports use the recount only when its database checksum matches.

## Snapshot v2026.10

Snapshot v2026.10 is the frozen June database (v2026.06) plus the October 2026 harvest of the catalogued resources it did not hold, one collection per record named `Renascor_<record id>`. The frozen database itself is never modified: the snapshot is built on a copy. See [harvest/README.md](../harvest/README.md) for the harvest, its deduplication and the records that could not be counted.

```bash
python3 scripts/rq_statistics.py --db /path/to/corpus_master.2026-10-14.v2026.10.sqlite --rq-root /path/to/RQ --snapshot v2026.10
python3 scripts/language_breakdown.py --db /path/to/corpus_master.2026-10-14.v2026.10.sqlite
python3 scripts/corpus_timeline.py --db /path/to/corpus_master.2026-10-14.v2026.10.sqlite
python3 scripts/build_site.py
```

With a later snapshot, records from the frozen corpus are relabelled, not recounted, because their collections are copied unchanged (some records hold hand-split shares of one collection). Harvested records get their words and texts from their own harvest and keep their curated languages and period, since the harvest assigns some languages and dates by approximation. The language breakdown leaves harvested collections out for the same reason. A record that also holds frozen copies of the same files (OpenEDGeS) takes its size from the harvest; both count towards its deduplicated corpus contribution.

## Period graph

The graph uses deduplicated words from the same working snapshot. Recorded harvest years, which can themselves be inferred, remain separate from newly estimated dates. Dates are not consistently composition or publication dates. Other filters select catalogue collections, including all languages in a multilingual collection.

For missing Gutenberg years, the estimator reads the author lifespan from saved harvest metadata and checks it against the selected author's death-year evidence. A single complete lifespan wholly within 1450–1700 is accepted as a broad proxy for the underlying work. No ebook release dates, modern edition filename dates, arbitrary point dates or collection-wide date spans are substituted. Missing or conflicting lifespans and ranges crossing the scope are retained for review.

For display, estimated words are allocated equally per year across the lifespan, then aggregated by decade. Integer largest-remainder allocation preserves each text's exact word count, including 1700 in the last bin. This is a visual convention, not evidence that production was uniform or a statistical probability model. Estimated words appear in the same solid bars as recorded-year words; the methodology and hover labels explain their contribution. Catalogue coverage derived from these ranges is labelled approximate. Words without usable evidence stay unallocated; the frozen database and corpus totals remain unchanged.

Detailed estimated and unallocated word totals remain in the text-free audit; the page gives only a brief explanation that the graph is approximate. The period controls show a brief message only when the selected collections have no chronological corpus counts.

```bash
python3 scripts/corpus_timeline.py --db /path/to/corpus_master_FROZEN_2026-06-26.sqlite
python3 scripts/build_site.py
```

The text-free [period audit](../data/period_word_counts.json) conserves the complete corpus counts and records date-confidence labels, each inferred range, source metadata evidence and review reasons. The displayed graph covers only mapped catalogue collections; internal or excluded sources remain in the audit. Later collection censuses, restored pre-deduplication texts and collections without date evidence do not enter this graph. Regenerate the audit after changing `scripts/rq_families.json`; normal site builds need neither the private database nor its texts.

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

The [CORDIS review](CORDIS_REVIEW.md) records the first search for missing EU-funded text collections. Its [metadata audit](../data/cordis_review_2026-10-09.json) preserves coverage, archive checksums, search expressions and candidate evidence. Review candidates before creating files in `data/entries`; the audit itself does not add catalogue records.

[.github/FUNDING.yml](../.github/FUNDING.yml) configures GitHub’s Sponsor button to link to [Ko-fi](https://ko-fi.com/clementgodbarge).

## Languages per entry

Multilingual entries harvested into the Renascor Corpus record how many texts and words each language contributes (`language_counts`); a language with three texts or fewer names them, from `scripts/isolated_titles.json`. Regenerate after changing `scripts/rq_families.json` or the titles file:

```
python3 scripts/language_breakdown.py --db /path/to/corpus_master.sqlite
python3 scripts/build_site.py
```
