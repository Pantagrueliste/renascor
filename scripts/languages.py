"""Language labels used by the catalogue, independently of source classifications."""

REMOVED_LABELS = {"multilingual", "romance", "romance (other)"}
GREEK_LABELS = {"ancient greek", "modern greek"}


def catalogue_languages(values):
    """Merge Greek varieties, drop non-language labels and retain input order."""
    result = []
    for value in values:
        label = value.strip()
        key = label.casefold()
        if not label or key in REMOVED_LABELS:
            continue
        if key in GREEK_LABELS:
            label = "Greek"
        if label not in result:
            result.append(label)
    return result
