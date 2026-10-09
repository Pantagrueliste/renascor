# Contributing to Renascor

Thank you for helping to build this catalogue. There are two ways to contribute, and neither requires technical expertise.

## Option 1: Open an issue (recommended for most people)

Use the [new entry form](https://github.com/Pantagrueliste/renascor/issues/new?template=new-entry.yml).

The form asks for the essential details about a digital edition project. Fill in what you know; leave blank what you do not. A maintainer will review your submission, format it as a catalogue entry, and add it to the dataset.

## Option 2: Edit files directly

If you are comfortable with Git and JSON, you can add an entry yourself.

### Steps

1. Fork the repository.
2. Create a new file in `data/entries/` named after the project, for example `data/entries/textgrid-repository.json`. Use lowercase letters, digits, and hyphens only.
3. Write the entry as JSON. The required fields are defined in [`schema/entry.schema.json`](schema/entry.schema.json) and explained in [`schema/README.md`](schema/README.md). You can copy an existing entry as a template. If the edition's TEI XML (or other machine-readable files) can be downloaded, give that address in `data_url` and the files' format in `data_format`.
4. Run the validation script locally:

   ```bash
   python scripts/validate_entry.py data/entries/your-file.json
   ```

5. Commit your change and open a pull request.

### What happens next

A GitHub Action automatically checks every pull request:

- validates the entry against the schema
- checks that the URLs resolve (the edition's `url` and, if given, its `data_url`)
- flags probable duplicates (same URL or very similar title)

A human maintainer then reviews the entry and merges it.

## What we accept

We catalogue projects that provide digital editions of Renaissance-era written documents (roughly 1450 to 1700):

- **Manuscript editions** (transcriptions, diplomatic editions)
- **Printed works** (editions of early printed books)
- **Correspondence** (letters, diplomatic documents, archives)

We record the project, not individual texts. A project may contain one text or thousands.

### Geographical and historical scope

“Renaissance” is a historical and cultural framework centred on Europe, particularly Western Europe; **1450–1700** supplies its chronological limits. We also include texts arising from documented contacts between European societies and other populations, including trade, diplomacy, travel, migration, missions and colonial encounters. Texts by any community involved are eligible, wherever written and in any language. Connected traditions are considered in their own historical contexts.

For a collection outside the European focus, explain the relevant historical connection and identify the texts concerned. A date within 1450–1700 alone does not establish geographical relevance. Broader repositories may qualify through an identifiable subset; describe that subset and the counting coverage.

### The inclusion rule: text collections

A resource must provide an identifiable collection of transcribed or editorially corrected Renaissance texts. Collections, anthologies and repositories can qualify even when they reproduce texts available in other catalogued resources. A directory or search portal without a text collection does not qualify.

The texts must be freely accessible. Collections requiring payment or a subscription are excluded, even if metadata, previews or temporary trials are free. Free access does not establish a reuse licence: record the text licence separately.

If the collection, edition or archived text dataset has a DOI, record it in `doi`. Verify what it identifies; do not substitute a grant DOI or the DOI of an article about the resource.

Record the resource’s own `words` and `texts` within **1450–1700, before content deduplication**. Give the source, counting method and coverage; identify partial harvests explicitly. Omit counts that have not been established rather than guessing or entering zero. A missing count can be completed after the resource has been reviewed.

Content deduplication belongs to the parallel **Renascor Corpus Project**. Where available, `corpus_statistics` records a resource’s contribution after that process, separately from its catalogue size. Overlapping text does not justify rejecting a collection, though the same resource should not receive two catalogue records.

Active rejections and resources awaiting reconsideration are recorded separately in [`data/rejected.json`](data/rejected.json), with their reasons.

## What we do not accept

- Text collections requiring payment or a subscription
- Page images or facsimiles only, with no text layer
- Raw, uncorrected OCR without editorial review
- Catalogues or bibliographies that contain no texts
- Directories and federated search services that point to other projects without providing a text collection
- Projects outside the 1450 to 1700 window, unless the majority of their material falls within it

If you are unsure whether a project qualifies, submit it anyway and say so. Misclassification is easy to fix.

## Corrections

If you find an error in an existing entry, [open an issue](https://github.com/Pantagrueliste/renascor/issues/new?template=correction.yml) or propose a fix via pull request.

## Code of conduct

[Behave well.](CODE_OF_CONDUCT.md)
