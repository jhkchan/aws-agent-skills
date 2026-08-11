# Eval: missing-lf-tag-on-resource

**Difficulty:** medium
**Branch:** PREREQUISITES_MISSING — LF-tags must be attached to resources before tag-based grants can match

## Prompt

Deploy Lake Formation LF-tag based access control for the
analytics team. Data lake admin
arn:aws:iam::123456789012:role/LFDataLakeAdmin is registered.
LF-tag keys environment (production, staging) and department
(finance, engineering) are created. Attach LF-tags to database
analytics_db: environment=production. The target table
analytics_db.transactions HAS NO LF-TAGS ATTACHED (the operator
created the table but forgot to attach LF-tags —
get-resource-lf-tags returns empty). Grant LF-tag-based SELECT
to arn:aws:iam::123456789012:role/AnalyticsTeamRole on
environment=production AND department=finance. Database and
table exist. Account: 123456789012. Region: us-east-1.
