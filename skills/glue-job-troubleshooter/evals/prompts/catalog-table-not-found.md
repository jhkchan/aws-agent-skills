# Eval prompt: catalog-table-not-found

Diagnose the Glue job failure. Walk the seven-category diagnostic tree
and emit the standard diagnostic block (TARGET, VERDICT, REASON,
CATEGORY, EVIDENCE, REMEDIATION).

JobName: cross-account-reader (case catalog-table-not-found)
RunId: jr_cat112233445
Region: us-east-1
GlueVersion: 4.0

get-job-run output:
  State: FAILED
  ExecutionTime: 6
  ErrorMessage: "EntityNotFoundException: Table sales_raw not found"

Probe: aws glue get-table --database-name analytics_prod
  --name sales_raw (run with the job's IAM role)
  → AccessDeniedException: User is not authorized to perform
    glue:GetTable on resource
    arn:aws:glue:us-east-1:111122223333:table/analytics_prod/sales_raw

Probe: aws glue get-table (run with admin role)
  → Table exists, row count 14.2M, last crawled 2 hours ago.

Cross-account: catalog lives in account 111122223333; the Glue job
runs in account 444455556666.
