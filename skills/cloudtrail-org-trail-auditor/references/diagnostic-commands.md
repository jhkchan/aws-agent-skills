# Diagnostic Commands — cloudtrail-org-trail-auditor

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-trail`, `start-logging`, `stop-logging`, `add-tags`, `put-insight-
  selectors`), the auditor MUST emit:
  `CONFIRM: About to <action> on trail <name> in account <account>. This
  affects <consequence>. Proceed? (yes/no)` and wait for an explicit `yes`
  before emitting the CLI. Treat `delete-trail` as BLOCKED — see the NEVER
  list.

- **Capture current trail config for rollback:**
  `aws cloudtrail describe-trails --trail-name-list <name> --output json >
  /tmp/<name>-backup-$(date +%s).json` BEFORE any modification. Trail updates
  are not versioned — there is no undo without a backup.

- **Enabling Insights incurs cost.** `put-insight-selectors` starts billing
  per management event analyzed. Surface this BEFORE the operator approves —
  do not silently enable a metered feature.

- **update-trail is atomic but irreversible.** Changing `KmsKeyId` from null
  to a key ARN re-enables SSE-KMS encryption going forward but does NOT
  re-encrypt existing log files already in S3. Old files remain under
  whatever encryption they were delivered with.

- **Org-trail enablement check.** Before recommending `update-trail
  --is-organization-trail`, verify the caller is in the management account
  and that `aws organizations describe-organization` returns a valid org.
  A member account cannot create or update an org trail.
