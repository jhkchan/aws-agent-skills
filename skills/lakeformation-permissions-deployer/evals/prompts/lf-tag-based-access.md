# Eval: lf-tag-based-access

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — full checklist with admin, LF-tag keys, tag attachment, tag-based grant

## Prompt

Deploy Lake Formation LF-tag based access control for the
analytics team. Register data lake admin
arn:aws:iam::123456789012:role/LFDataLakeAdmin (already exists
in IAM). Create LF-tag keys: environment (values: production,
staging, dev), department (values: finance, engineering,
marketing), sensitivity (values: public, internal, restricted,
pii). Attach LF-tags to database analytics_db:
environment=production, department=finance. Attach LF-tags to
table analytics_db.transactions: environment=production,
department=finance, sensitivity=restricted. Grant LF-tag-based
SELECT and DESCRIBE to principal
arn:aws:iam::123456789012:role/AnalyticsTeamRole on TABLE
resources matching environment=production AND department=finance.
Target Glue database analytics_db and table transactions both
exist. Account: 123456789012. Region: us-east-1.
