# Eval prompt: bookmark-not-advancing-layout-drift

Diagnose why the Glue job is reprocessing data. Walk the seven-category
diagnostic tree and emit the standard diagnostic block (TARGET, VERDICT,
REASON, CATEGORY, EVIDENCE, REMEDIATION).

JobName: hourly-events-rollup (case bookmark-not-advancing-layout-drift)
RunId: jr_xyz987abc321
Region: us-east-1
GlueVersion: 3.0

get-job-run output:
  State: SUCCEEDED
  ExecutionTime: 47
  ErrorMessage: ""

Symptom: job reprocesses ~100% of source bytes on every run.
Source S3 prefix was s3://events/year=2025/month=08/... until yesterday;
today it is s3://events/dt=2025-08-09/...

get-job-bookmark output:
  JobBookmarks:
    - Attempt: 12
      Args:
        partitionKeys: ["year", "month"]

Job argument --job-bookmark-option: enable
Job IAM role: includes glue:GetJobBookmark and glue:UpdateJobBookmark
(Allow).
