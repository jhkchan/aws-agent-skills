# Diagnostic commands - CUR Automation Automator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Pre-flight: requirement gate — live-account commands

1. `aws organizations describe-organization` — confirm the caller is
   the payer / management account. If not, CUR scope is limited.
2. `aws cur describe-report-definitions` — confirm whether a CUR with
   the target name already exists (create vs. update).
3. `aws s3api get-bucket-location --bucket <cur-bucket>` and
   `get-bucket-versioning` — verify the CUR bucket exists, has
   versioning on, and is in the target region.
4. `aws s3api get-bucket-policy --bucket <cur-bucket>` — verify the
   policy grants `billingreports.amazonaws.com` WRITE and
   `athena.amazonaws.com` READ, with `aws:SourceAccount` conditions.
5. `aws glue get-database --name <athena_db>` — verify the Glue database
   exists (or will be created alongside the template).
6. `aws athena list-work-groups` — verify a non-`primary` workgroup
   exists with `EnforceWorkgroupConfiguration: true` and a per-query
   byte cutoff.
7. `aws quicksight describe-account --aws-account-id <acct>` (if
   QuickSight requested) — verify `AccountEdition: ENTERPRISE`.
8. `aws ce list-cost-allocation-tags --status Active` (if tags layer
   requested) — verify the target tag keys are already activated.
9. `aws ce list-cost-category-definitions` (if chargeback requested) —
   verify existing Cost Categories to avoid name conflicts.
10. `aws bcm-data-exports list-exports` (if BCM Data Exports requested)
    — verify the service is enabled.

## Diagnostic flows

### CUR not delivering to S3

`aws s3 ls s3://<bucket>/<prefix>/year=YYYY/month=MM/` — empty for >
24 hours is almost always a bucket policy problem. Verify
`billingreports.amazonaws.com` is present with `aws:SourceAccount`
condition, and that the bucket region matches `S3Region` in the report
definition.

### Athena query fails with "HIVE_CURSOR_ERROR"

The CUR table schema is out of date — AWS adds columns when new
services launch. Pull the latest DDL from the AWS docs or
`aws cur get-report-definition`. Use `OPENCSVSerde` for legacy CSV CUR;
`ParquetHiveSerDe` for Parquet.

### Athena query returns "Partition not found"

Partition projection not enabled, or partition date outside range.
Check `TBLPROPERTIES ('projection.enabled' = 'true')` and
`projection.day.range = '2024/01/01,NOW'`. The literal `NOW` is
evaluated at query time — requires Athena engine v3.

### QuickSight SPICE refresh fails with "Athena query timeout"

The auto-generated SQL scans too much data without a partition
predicate. Add a filter on the partition column in the QuickSight
dataset, or use a custom SQL dataset with a WHERE clause.

### Tag activation has no effect on CUR data

The tag was activated AFTER the data was delivered. CUR does NOT
backfill — historical data remains tag-less. Activation applies only
to data delivered after activation.
