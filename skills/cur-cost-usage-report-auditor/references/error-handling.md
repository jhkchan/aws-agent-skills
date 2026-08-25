# Error handling - CUR Cost and Usage Report Auditor

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Error handling — API and input failures

**IAM permission errors:** If `describe-report-definitions` returns
`AccessDeniedException`, the caller lacks `cur:DescribeReportDefinitions`.
Emit `VERDICT: ERROR` — this is an IAM failure, not a NO_CUR finding.
Required minimum policy for the auditor role: `cur:DescribeReportDefinitions`,
`s3:ListBucket`, `s3:GetObject`, `glue:GetTable`. Verify with
`aws iam simulate-principal-policy` before reporting NO_CUR.

**API throttling:** The CUR API has a low TPS limit (~1 TPS per payer
account). For multi-account sweeps, serialize calls with 1s delay. If
`ThrottlingException` occurs, retry with exponential backoff (2s, 4s, 8s).

**Malformed input:** If the report-definition JSON is invalid (missing
required fields, non-parseable), emit `VERDICT: ERROR` with the specific
field name. Do NOT attempt classification on malformed input — a missing
`TimeUnit` or `Format` field makes staleness and CONFIG_GAP checks
unreliable.

**Missing manifest with bucket access:** If `list-objects-v2` returns
empty but the bucket exists and has objects, verify the prefix path
matches `S3Prefix + "/" + ReportName + "/"`. A trailing-slash mismatch
is the most common cause of "no manifest found" false positives.
