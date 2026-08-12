# Eval prompt: s3-bucket-access-denied-glue-ok

Diagnose the Athena query failure for the following table. Walk the
symptom-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: Athena query fails with "QUERY_FAILED: Access Denied
s3://prod-data-lake/events/data.parquet". The error is on the S3 read,
not on Glue catalog access.

```text
Database: analytics
Table: events
Query: SELECT * FROM analytics.events LIMIT 10
QueryStatus: FAILED
StateChangeReason: "Access Denied s3://prod-data-lake/events/data.parquet"

Table LOCATION: s3://prod-data-lake/events/

IAM simulate-principal-policy:
  glue:GetTable on arn:aws:glue:us-east-1:111111111111:table/analytics/events → ALLOWED
  glue:GetPartitions → ALLOWED
  glue:GetDatabase → ALLOWED
  s3:GetObject on arn:aws:s3:::prod-data-lake/* → DENIED (implicitDeny)
  s3:ListBucket on arn:aws:s3:::prod-data-lake → DENIED (implicitDeny)

S3 bucket policy:
  (bucket policy does not grant access to the Athena role; relies
   on IAM which is missing the s3 actions)

Lake Formation: not enabled on this catalog

Workgroup: primary
```

Athena has two independent permission layers: Glue Data Catalog and
S3 data bucket. The Glue permissions pass; the S3 permissions fail.
Adding Glue permissions does not fix the S3 denial.
