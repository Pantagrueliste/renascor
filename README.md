# Renascor

An open catalogue of digital editions of Renaissance-era written documents: manuscripts, printed works, and correspondence.

The name blends Latin *renascor* ('I am reborn') with 'corpus'.

## What this is

Renascor records projects that have produced digital editions of texts from roughly 1450 to 1700. Each entry describes one edition project: who made it, what it contains, in which language, in which format, and where to find it.

This is a catalogue of editions, not a corpus of texts. We do not host the texts themselves. We point to them.

## What is in an entry

Every entry in `data/entries/` is a single JSON file describing one edition project. The full field list is defined in `schema/entry.schema.json`. At minimum, each entry records:

- the title of the project or collection
- the URL where the edition can be found
- the language or languages of the texts
- the encoding format (TEI, HTML, Markdown, or other)
- whether the project is active or archived
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

The running cost of the automated search is under one cent per week. Without this assistance, the catalogue would grow much more slowly, and some corners of the landscape would likely remain unexplored. The assistance is a tool, not a replacement for judgement: the editorial decisions are human.

## The public site

The catalogue is published as a static website at [renascor.github.io](https://renascor.github.io) (or your GitHub Pages URL). The site is generated from the JSON files in `data/entries/` and offers:

- search across all entries
- filters for language, period, region, encoding, and status
- download of the full dataset as CSV or JSON

### Running the site locally

```bash
# Build the site data from entries
python scripts/build_site.py

# Serve the site locally (Python 3)
python -m http.server 8000 --directory docs
```

Then open http://localhost:8000 in your browser.

## Licence

- **Data** (the JSON files in `data/entries/`): [CC0 1.0 Universal](LICENSE-DATA). You may use, modify, and share the data for any purpose, with no obligation to attribute.
- **Code** (scripts, site generator): [MIT Licence](LICENSE).

## Citation

If you use this catalogue in your research, please cite it. See [CITATION.cff](CITATION.cff).

## Support this project

Renascor runs on a few dollars a month. Donations cover the running costs of the weekly automated search. If you find this catalogue useful, you can [buy me a coffee on Ko-fi](https://ko-fi.com/clementgodbarge).

## Contact

Clément Godbarge, Lecturer in Digital Humanities, University of St Andrews.
test
