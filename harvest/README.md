# October 2026 harvest

The Renascor Corpus snapshot v2026.10 adds to the frozen June working corpus (v2026.06) the texts of the catalogued resources that it did not hold. This directory contains the code and the text-free records of that harvest. The texts themselves stay outside the repository, in `$RQ_ROOT/data/raw/renascor_2026-10/` (`RQ_ROOT` defaults to `../RQ` beside this repository).

## Contents

- `hlib.py`: helpers shared by the harvest scripts (polite fetching, caching, staging records in the RQ ingest format, report).
- `scripts/<id>.py`: one script per catalogue record, plus a few helpers for multi-step harvests. `HARVEST.md` gives the rules the scripts follow: period text only, one diplomatic version when several are offered, dates of the sources, partial harvests documented.
- `reports.json`: what was harvested for each record, its coverage and its known problems.
- `fingerprint.py`, `dedup.py`: duplicate detection against the frozen corpus and between harvested texts.
- `duplicates.json`: every harvested text found to duplicate another text, with the kind of match.
- `build_snapshot.py`: builds the snapshot database; `ingest.json` records what it ingested.

## Counting and deduplication

Texts are counted with the corpus's own tools (`rqfootprint.textstats`, the `ingest_texts` language normaliser, 1450–1700 window and filter for texts under 20 words). Duplicates follow the corpus policy: a harvested text is flagged `is_dup=1` when its normalised word sequence equals another text's, or when it is a near-copy (at least 80% of sampled five-word sequences in common) of a text from the same upstream files. Those are the same resource, or a corpus collection that took its texts from that resource: TextGrid_German for the TextGrid Repository, OpenEDGeS for the OpenEDGeS Bibles, Corpus Corporum for Poeti d'Italia in lingua latina. Independent editions or transcriptions of the same work stay counted as separate witnesses.

Two corrections were applied to the staging files after the harvest. Undated Hartlib Papers files are counted in the window, since Hartlib died in 1662. Three Lüne letters dated 1423-1438 are kept out of it.

## Rebuilding

```bash
python3 harvest/scripts/<id>.py                      # for each record (network; cached files are reused)
python3 harvest/fingerprint.py index-rq rq_index.sqlite   # fingerprints of the frozen corpus
python3 harvest/fingerprint.py index-dirs rq_index.sqlite # corpus collections stored as whole raw files
python3 harvest/dedup.py rq_index.sqlite duplicates.json
python3 harvest/build_snapshot.py duplicates.json corpus_master.2026-10-13.v2026.10.sqlite
```

Then refresh the catalogue as described in [docs/MAINTENANCE.md](../docs/MAINTENANCE.md#snapshot-v202610).

## Not counted

Six records have no harvested count: 1641 Depositions (reCAPTCHA), Briefwisseling Constantijn Huygens and the Divisiekroniek (the Huygens server refuses automated clients), The Chymistry of Isaac Newton (robots.txt disallows the manuscript pages), CODEA+ 2022 (its licence forbids reuse in a corpus) and the Rostock matriculation portal (short name records, under the 20-word filter). Some other harvests are partial; `reports.json` and the record notes say which.

The Rostocker Urgichten repository puts its file downloads behind a bot check. Their 50 TEI files, listed through its open OAI-PMH interface, were downloaded once in a browser with `files/manual/download_in_browser.js`; `scripts/rostocker-urgichten.py` stages the saved file. No bot check is bypassed by the harvest code.
