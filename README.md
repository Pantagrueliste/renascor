# Renascor

An open catalogue of digital editions of Renaissance-era written documents: manuscripts, printed works, and correspondence.

## What this is

Renascor records projects that have produced digital editions of texts from roughly 1450 to 1700. Each entry describes one edition project: who made it, what it contains, in which language, in which format, and where to find it.

This is a catalogue of editions, not a corpus of texts. We do not host the texts themselves. We point to them.

A resource is added only if it brings new, countable text: the number of words it contributes can be counted exactly, and its texts are verifiably not already in the catalogue. Portals and aggregators that federate other projects' texts are not included. See [CONTRIBUTING.md](CONTRIBUTING.md#the-inclusion-rule-new-countable-text).

## What is in an entry

Every entry in `data/entries/` is a single JSON file describing one edition project. The full field list is defined in `schema/entry.schema.json`. At minimum, each entry records:

- the title of the project or collection
- the URL where the edition can be found
- the language or languages of the texts
- the encoding format (TEI, other XML, HTML, plain text, wiki markup, Markdown, or other)
- whether the project is active, archived, or discontinued (no longer online)
- how the entry was added (submitted by a contributor, or discovered by automated search)
- the date the entry was added

## How to contribute

There are two ways to add an entry:

1. **Open an issue.** Use the [new entry form](https://github.com/Pantagrueliste/renascor/issues/new?template=new-entry.yml). You do not need to know Git or JSON.
2. **Edit a file directly.** Add a JSON file to `data/entries/` and open a pull request. See [CONTRIBUTING.md](CONTRIBUTING.md) for the format.

Every contribution is reviewed by a human before it appears in the catalogue.

## How this catalogue is built

This catalogue is maintained with AI assistance. A weekly automated search uses a Mistral language model to find new digital edition projects on the web. The model proposes candidates; it does not add them to the catalogue.

Every automatically discovered entry is reviewed by a human before publication. The reviewer checks that the project is real, that it provides digital editions (not just page images), that the source material falls within the project's scope, and that the metadata is accurate. Entries contributed by humans through the issue form or pull requests are also reviewed.

The running cost of the automated search is a few cents per week. Without this assistance, the catalogue would grow much more slowly, and some corners of the landscape would likely remain unexplored. The assistance is a tool, not a replacement for judgement: the editorial decisions are human.

## The public site

The catalogue is published as a static website at [renascor.github.io](https://renascor.github.io) (or your GitHub Pages URL). The site is generated from the JSON files in `data/entries/` and offers:

- a table of all editions (or cards), sortable by title, words, texts, period, encoding and status
- search across titles, institutions, languages and notes
- filters for language, period (any range of years, chosen on a timeline), encoding, status and size, combined freely; a files filter (the format of the files that can be downloaded) and an area filter (once countries are recorded) appear when the data carry them
- a full record for each edition, with a permanent link
- links that keep the current search and filters, so a selection can be shared
- export of the editions shown, and download of the whole catalogue, as CSV or JSON with every field
- a methodology section explaining where the figures come from

### Running the site locally

```bash
# Build the site data from entries
python scripts/build_site.py

# Serve the site locally (Python 3)
python -m http.server 8000 --directory docs
```

Then open http://localhost:8000 in your browser.

`build_site.py` validates the entries and writes `docs/data.json`, `docs/renascor.csv` and `docs/renascor.json`. It also writes the catalogue figures and the two charts of the methodology section into `docs/index.html`, so run it after any change to the data. A second run changes nothing. To try the page on other data without touching `docs/`, build into another directory, which receives a copy of the page and its script:

```bash
python scripts/build_site.py --entries-dir /path/to/entries --out-dir /tmp/renascor-site
```

The unit tests of the build run with `python -m unittest discover -s tests -v`.

## Licence

- **Data** (the JSON files in `data/entries/`): [CC0 1.0 Universal](LICENSE-DATA). You may use, modify, and share the data for any purpose, with no obligation to attribute.
- **Code** (scripts, site generator): [MIT Licence](LICENSE).

## Citation

If you use this catalogue in your research, please cite it. See [CITATION.cff](CITATION.cff).

## Support this project

Renascor runs on a few dollars a month. Donations cover the running costs of the weekly automated search. If you find this catalogue useful, you can [buy me a coffee on Ko-fi](https://ko-fi.com/clementgodbarge).

## Contact

Clément Godbarge, Lecturer in Digital Humanities, University of St Andrews.
