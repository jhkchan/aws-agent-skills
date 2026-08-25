# Diagnostic Commands (load on demand) — AWS DataSync Task Operator

Live-account pre-flight command listing and pre-flight safety checks
moved verbatim from SKILL.md. Loaded on demand.

---

## Pre-flight — live-account command listing (moved from SKILL.md)



**Live-account pre-flight (skip if offline plan audit):**
1. `aws datasync list-agents` — confirm an agent exists, capture
   `AgentArn`. `describe-agent` returns `LastConnectionTime`,
   `Status`. Anything older than 5 minutes or `Status != ONLINE`
   is BLOCKED.
2. `aws datasync list-locations` — find source and destination
   `LocationArn` and capture their `LocationUri` and `LocationType`.
3. For S3 sources: `aws s3api get-bucket-location`,
   `get-bucket-encryption`, `get-bucket-versioning`.
4. For S3 destinations: same set as #3, plus `get-bucket-policy`
   (cross-account), `get-bucket-ownership-controls`.
5. For EFS destinations: `aws efs describe-file-systems`,
   `describe-mount-targets` — confirm `available` and a mount target
   exists in the agent's subnet.
6. For FSx family destinations: `aws fsx describe-file-systems` and
   the file-system-specific describe call. Confirm `Lifecycle:
   AVAILABLE` and the agent subnet has network reachability.
7. `aws iam list-attached-role-policies --role-name <task-role>` and
   `list-role-policies` — verify the task role's permission chain.
8. `aws kms describe-key --key-id <destination-key>` — confirm
   `Enabled` and key policy grants the task role.
9. `aws datasync describe-task --task-arn <task>` — capture
   `CurrentTaskExecutionArn`, `Status`, `Options`, `Schedule`.
10. `aws datasync describe-task-execution --task-execution-arn <arn>`
    for the most recent execution — capture `Status`,
    `BytesTransferred`, `FilesTransferred`, `EstimatedFilesToTransfer`,
    `VerificationFilesFailed`, `ErrorCode`, `ErrorDetail`.
11. For discovery: `aws datasync list-discovery-jobs` — confirm no
    in-flight discovery job covers the same storage system.



## Pre-flight safety checks (run before any remediation CLI) (moved from SKILL.md)



- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-task`, `update-task`, `start-task-execution`,
  `delete-task`, `create-agent`, `update-task-schedule`,
  `start-discovery-job`), emit: `CONFIRM: About to <operation> on
  <task> in account <account> region <region>. This will
  <consequence>. Proceed? (yes/no)`. Do NOT execute until the
  operator confirms.

- **Capture pre-state for rollback.** Before any task change:
  `aws datasync describe-task --task-arn <task> --output json >
  /tmp/<task>-pre-$(date +%s).json`. This is the only rollback path
  — `update-task` is full-replacement of `Options`.

- **Verify agent health before any execution.** An offline agent
  produces `Status: LAUNCHING` indefinitely on the execution; the
  diagnostic surface for that is poor. Check `describe-agent`
  `LastConnectionTime` < 5 min ago.

- **Verify KMS key policies, not just IAM.** Cross-account KMS
  requires the destination key policy to grant the task role. IAM
  alone is not sufficient.

- **Verify the destination bucket policy for cross-account S3.**
  Check for `s3:PutObject` grant with the source account condition.
  Without it, the task fails partway through with a misleading
  AccessDenied.

- **Prefer additive changes over destructive ones.** Adding a new
  task is reversible; deleting a task loses all execution history
  and Task Reports.

- **Validate `Includes`/`Excludes` filter scope before applying.**
  An empty filter transfers everything under the source location.
  Confirm intent — cost/time scales with bytes scanned.


