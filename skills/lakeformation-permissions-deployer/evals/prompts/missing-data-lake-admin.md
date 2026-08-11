# Eval: missing-data-lake-admin

**Difficulty:** hard
**Branch:** PREREQUISITES_MISSING — data lake admin required for LF-tag creation and permission grants

## Prompt

Deploy Lake Formation LF-tag based access control for the
analytics team. Data lake admin: NONE REGISTERED (the operator
forgot to register an admin — list-data-lake-settings returns
empty DataLakeAdmins list). Create LF-tag keys: environment
(production, staging), department (finance, engineering).
Attach LF-tags to database analytics_db and table transactions.
Grant LF-tag-based SELECT to principal
arn:aws:iam::123456789012:role/AnalyticsTeamRole. Target Glue
database analytics_db and table transactions both exist.
Account: 123456789012. Region: us-east-1.
