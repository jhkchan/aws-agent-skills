# Baseline (no-skill) response: format-conversion-0-byte

This file captures what a generic assistant produces WITHOUT the
kinesis-firehose-troubleshooter skill loaded - the contrast that
proves the skill adds structure (5-layer health check,
deterministic VERDICT, fix CLI, verification step).

---

The Parquet conversion is producing 0-byte files. This is
likely a schema mismatch between the Glue table and the input
JSON. Your Glue columns use CamelCase but the JSON keys use
snake_case.

You should update the Glue table to match the JSON field names,
or enable case-insensitive matching on the OpenXJsonSerDe.
