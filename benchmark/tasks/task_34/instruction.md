Read `file_parser.py` and `data.csv` in full before making any changes.

I have two bugs in my `file_parser.py` file:

1. The `parse_csv()` function does not handle an empty file — it raises an unhandled `StopIteration` error when the CSV file is empty.
2. The `get_column()` function does not handle a missing column name — it raises an unhandled `KeyError` when the column does not exist in the CSV headers.

Please fix both bugs so that:
- `parse_csv(path)` raises a `ValueError` with the message `"CSV file is empty: {path}"` when the file has no data rows
- `get_column(rows, column)` raises a `ValueError` with the message `"Column not found: {column}"` when the column does not exist
