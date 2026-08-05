# Baseline (no-skill) response: column-wildcard-select-no-filter

This file captures what a generic assistant produces WITHOUT the
lakeformation-data-lake-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, ColumnWildcard vs ColumnNames distinction, DataCellsFilter
wiring gap).

---

The analyst role has SELECT on the customers_pii table with what looks like
a wildcard on columns. Since this table is tagged as PII, you should
restrict the columns to only what the analyst needs. Also there does not
appear to be a row-level filter set up.

Consider listing specific columns instead of the wildcard and adding a
data cells filter.
