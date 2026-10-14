Read `git_helper.py` and `COMMIT_LOG.txt` in full before making any changes.

I have two bugs in my `git_helper.py` file:

1. The `parse_commit()` function does not handle a malformed commit line — it raises an unhandled `ValueError` when the commit line does not contain the expected number of fields separated by `|`.
2. The `get_author_commits()` function does not handle an empty commit list — it raises an unhandled `ZeroDivisionError` when computing the average commits per author on an empty list.

Please fix both bugs so that:
- `parse_commit(line)` raises a `ValueError` with the message `"Malformed commit line: {line}"` when the line does not have exactly 4 fields
- `get_author_commits(commits, author)` returns an empty list instead of crashing when the commits list is empty
