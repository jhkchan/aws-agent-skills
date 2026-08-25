# Error Handling — cloudtrail-lake-operator

## Malformed input (EDS or query configuration)

**Malformed input:** if the input JSON is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: EDS or query configuration
is not valid JSON or is missing required fields — cannot plan.` and
`REMEDIATION: Re-fetch with aws cloudtrail get-event-data-store
--event-data-store <id> --output json and re-plan.`

## CloudTrail Lake failure-mode table (diagnose-empty-query / diagnose-slow-query)

**CloudTrail Lake failure-mode table (use during diagnose-empty-query
and diagnose-slow-query):**

| Symptom | Root cause | Fix |
|---|---|---|
| `QueryStatus: FINISHED`, `ResultsCount: 0`, EDS has events | EDS `EventCategory` list does not include the queried event source | `update-event-data-store` to add the missing category. |
| `ResultsCount: 0`, `eventTime` filter outside retention | Events aged out past `RetentionPeriod`. | Tighten the time window OR extend `RetentionPeriod` (only future events). |
| `ResultsCount: 0`, `awsRegion` filter wrong | Operator queried `region=...`; Lake column is `awsRegion`. | Fix SQL: `awsRegion = 'us-east-1'`. |
| `QueryStatus: FAILED`, `ErrorMessage: "Column not found"` | SQL references a non-Lake column. | Use only supported columns (`eventTime`, `eventSource`, `eventName`, `awsRegion`, `userIdentity.*`, etc.). |
| `QueryStatus: FAILED`, `ErrorMessage: "EDS not in this Region"` | Cross-Region query. | Use Athena federation OR move the query to the EDS's Region. |
| `QueryRunTimeInSeconds > 600`, `BytesScanned` huge | No partition pruning (missing `eventTime` filter). | Add `WHERE eventTime BETWEEN timestamp1 AND timestamp2`. |
| `QueryRunTimeInSeconds > 600`, `BytesScanned` moderate | Too many columns selected (`SELECT *`). | Select only needed columns; Lake is columnar. |
| `QueryStatus: FAILED`, `AccessDenied` | Caller missing `cloudtrail:GetQuery`/`StartQuery` on EDS ARN. | Attach the IAM policy. |
| `QueryStatus: FAILED`, `KMS AccessDenied` | Caller missing `kms:Decrypt` on EDS KMS key. | Grant `kms:Decrypt` to the caller. |
| Non-AWS `PutAuditEvents` returns `AccessDenied` | Partner event source not registered, or role missing `cloudtrail:PutAuditEvents`. | Confirm Partner registration; attach IAM policy. |
| `QueryStatus: FAILED`, `JOIN across Regions` | JOIN only works same-Region. | Use Athena federation with two connector instances. |
| Athena federated query returns `AccessDenied` | Lake Formation grant missing on connector Lambda. | `aws lakeformation grant-permissions --principal <connector-lambda-role> --permissions ...`. |
| QuickSight cannot connect | QuickSight role cannot assume Athena workgroup role. | Add trust policy on the Athena workgroup role. |
