# Baseline (no-skill) response: serde-csv-separator-mismatch

This file captures what a generic assistant produces WITHOUT the
athena-query-failure-troubleshooter skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, layer
identification, evidence-backed root cause, symptom-to-layer triage).

---

Your Athena query is returning NULL for some columns. This usually
means the table definition doesn't match the data format. Since
order_id contains the entire row, it looks like the columns are not
being split correctly.

Check the SerDe properties in your CREATE TABLE statement. You might
need to change the separator or use a different SerDe. Try dropping
and recreating the table with the correct delimiter. You can also
try using LazySimpleSerDe instead of OpenCSVSerDe if that works
better for your data.
