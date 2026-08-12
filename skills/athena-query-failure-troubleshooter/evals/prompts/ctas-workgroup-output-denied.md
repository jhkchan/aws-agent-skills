# Eval prompt: ctas-workgroup-output-denied

Diagnose the Athena CTAS query failure for the following query. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: `CREATE TABLE AS SELECT` query fails with "Access Denied
s3://aws-athena-query-results-111111111111-us-east-1/tables/...". The
operator expected the CTAS to write to
`s3://prod-analytics/summary/` (the external_location in the query),
but it is writing to the workgroup result bucket.

```text
Query:
  CREATE TABLE analytics.orders_summary
  WITH (external_location = 's3://prod-analytics/summary/')
  AS SELECT order_id, SUM(amount) as total
  FROM analytics.orders_csv
  GROUP BY order_id;

QueryStatus: FAILED
StateChangeReason: "Access Denied s3://aws-athena-query-results-111111111111-us-east-1/tables/q=..."

Workgroup: primary
EnforceWorkGroupConfiguration: true
OutputLocation: s3://aws-athena-query-results-111111111111-us-east-1/

IAM simulate-principal-policy:
  s3:PutObject on arn:aws:s3:::prod-analytics/* → ALLOWED
  s3:PutObject on arn:aws:s3:::aws-athena-query-results-111111111111-us-east-1/* → DENIED (implicitDeny)

Glue permissions: verified (glue:CreateTable, glue:UpdateTable allowed)
Source table S3 permissions: verified (s3:GetObject on prod-analytics allowed)
```

The CTAS output location is determined by the workgroup configuration,
not the query's `external_location` when `EnforceWorkGroupConfiguration`
is true. The IAM role needs `s3:PutObject` on the workgroup result
bucket, not the source bucket.
