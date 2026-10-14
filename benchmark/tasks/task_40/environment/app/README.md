# Formatter Helpers

The test suite covers two helpers:

- `slugify(text)`: lowercase the text, collapse non-alphanumeric separators into single dashes, and trim leading or trailing dashes
- `truncate_words(text, max_words)`: return at most `max_words` words without adding extra words
