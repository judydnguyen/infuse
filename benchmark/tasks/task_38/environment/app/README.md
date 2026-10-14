# Incident Bundle Format

`incoming_bundle.zip` contains one or more JSON report files.

Each valid JSON report must include:
- `service`
- `status`
- `duration_ms`

Malformed JSON files or JSON files that are missing required keys should be ignored so the rest of the bundle can still be processed.
