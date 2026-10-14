I have a bug in my `process_zip.py` script. It reads `input.zip`, finds all CSV files inside, and prints a sales summary. However it crashes with a `KeyError` if any CSV file is missing the expected `sales` or `expenses` columns, instead of skipping that file gracefully.

Please fix `process_zip.py` so that:
- If a CSV file is missing the `sales` or `expenses` column, the file is skipped with a warning printed to stdout (e.g. `"Skipping <filename>: missing required columns"`)
- All valid CSV files are still processed and summarised correctly
- The script does not crash on malformed input
