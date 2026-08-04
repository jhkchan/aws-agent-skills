# Baseline (no-skill) response: config-gap-legacy-no-resources

This file captures what a generic assistant produces WITHOUT the
cur-cost-usage-report-auditor skill loaded.

---

This CUR has daily granularity with Parquet format and Athena enabled,
which covers the basics. The data is fresh.

A few things to note:
- The report version is "legacy-v0" instead of the current cur-1.0.
  You should update this.
- AdditionalSchemaElements is empty, so you won't have resource-level
  cost data.
- RefreshClosedReports is false, which means past billing periods won't
  be updated with late corrections.

The bucket has versioning enabled which is good.
