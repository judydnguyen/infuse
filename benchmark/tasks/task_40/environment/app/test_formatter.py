from formatter import slugify, truncate_words


def test_slugify_collapses_separators():
    assert slugify("Hello,   World!") == "hello-world"


def test_slugify_trims_surrounding_dashes():
    assert slugify("  Python__Rocks  ") == "python-rocks"


def test_truncate_words_limits_word_count():
    assert truncate_words("one two three four", 2) == "one two"


def test_truncate_words_keeps_short_text():
    assert truncate_words("short text", 5) == "short text"
