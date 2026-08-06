# Baseline (no-skill) response: datasource-stopped-incomplete

This file captures what a generic assistant produces WITHOUT the
detective-investigation-coverage-auditor skill loaded.

---

Your Detective graph is set up with all 3 accounts enabled. However,
account 333333333333 has its DETECTIVE_CORE data source in STOPPED state,
which means it is not contributing data to the behavior graph.

You should re-enable the data source package for that account. Also note
that its last data received timestamp is 8 days old, confirming it is not
actively ingesting.
