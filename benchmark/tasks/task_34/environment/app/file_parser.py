"""CSV file parser module."""
import csv
import os


def parse_csv(path):
    # BUG: does not handle empty file
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if len(rows) == 0:
            next(iter([]))  # raises StopIteration
        return rows


def get_column(rows, column):
    # BUG: does not handle missing column
    return [row[column] for row in rows]


def filter_rows(rows, column, value):
    return [row for row in rows if row.get(column) == value]


def count_rows(rows):
    return len(rows)


def get_headers(rows):
    if not rows:
        return []
    return list(rows[0].keys())


if __name__ == "__main__":
    rows = parse_csv("data.csv")
    print(get_headers(rows))
    print(get_column(rows, "name"))
