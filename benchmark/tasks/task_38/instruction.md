Read `README.md` and `summarize_bundle.py` in full, and inspect the contents of `incoming_bundle.zip`, before making any changes.

The current script crashes whenever a bundle contains malformed JSON or JSON reports missing required keys.

Please fix `summarize_bundle.py` so that:
1. Malformed JSON reports are skipped with a warning printed to stdout in the form `Skipping <filename>: invalid report`.
2. JSON files missing any required key are also skipped with the same warning format.
3. Valid reports are still returned and summarized correctly.
4. `summarize_records()` should only use valid reports.
5. Create `reports/summary.md` with short sections titled:
- Overview
- Fix
- Validation

Do not delete `incoming_bundle.zip`.
