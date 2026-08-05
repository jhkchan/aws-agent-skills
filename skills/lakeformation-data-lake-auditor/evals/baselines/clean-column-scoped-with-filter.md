# Baseline (no-skill) response: clean-column-scoped-with-filter

This file captures what a generic assistant produces WITHOUT the
lakeformation-data-lake-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, OK
rationale citing Step 9 conditions, defense-in-depth recommendations).

---

The sales-analyst role has SELECT on three specific columns (order_id,
total, region) of the orders table. There is a row filter restricting
rows to the US region. The table sits under the registered sales location
and the break-glass admin role is configured.

This configuration looks fine — column-scoped, row-filtered, and on a
registered path.
