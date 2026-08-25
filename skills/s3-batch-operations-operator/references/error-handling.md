# Error Handling — S3 Batch Operations Operator

Load-on-demand failure-mode reference moved verbatim from SKILL.md.

## Job failure-mode table (use during diagnose-job)


| Symptom in `describe-job` / completion report | Root cause | Fix |
|---|---|---|
| `Status: Failed` immediately after `Active` | Role could not be assumed, or manifest unreadable | Verify role trust policy allows `batchoperations.amazonaws.com`; verify `s3:GetObject` on manifest |
| `Status: Complete`, `Failed` > 0 with `AccessDenied` | Role missing operation-specific grant on a subset of objects (KMS key, cross-account bucket) | Add grant for the affected objects; re-run a scoped job targeting only failures |
| `Status: Complete`, `Failed` > 0 with `NoSuchKey` | Manifest references deleted objects, or CSV has a header row | Filter the manifest; never include a CSV header |
| `Status: Complete`, `Failed` > 0 with `SlowDown` / `Throttling` | Source or destination bucket throttled | Lower `RequestsPerSecond`; re-run failed objects |
| `Status: Active` for >> `CompletionWindow` | Manifest much larger than estimated, or persistent throttling | Check `ProgressSummary.TotalNumberOfTasks`; lower rate or cancel |
| `Status: Suspended`, never goes `Active` | `ToggleEnabled: false` at creation | `update-job-status --status-update Ready` (also requires `RequestedJobStatus: Ready`) |
| Lambda invoke failures with `ResourceConflictException` | Lambda reserved concurrency exhausted | `put-function-concurrency --reserved-concurrent-executions <rate>` |
| Lambda invoke failures with `Timeout` | Lambda timeout too short for per-object work | `update-function-configuration --timeout 60` (or higher) |
| Glacier restore "complete" but objects still `ongoing-request="true"` | Restore is asynchronous; `Status: Complete` only means requests were submitted | Poll `head-object --restore` per object; not a Batch Operations failure |
