# Advanced Patterns (load on demand) — CloudFormation Stack Rollback Troubleshooter

Step-0 expert-knowledge deep dives moved verbatim from SKILL.md. Loaded on demand.

---

## Step 0 — non-obvious behaviours that change rollback diagnosis (moved from SKILL.md)

- **`continue-update-rollback --resources-to-skip` is the canonical fix
  for UPDATE_ROLLBACK_FAILED.** It retries the rollback from the point
  of failure. Resources listed in `--resources-to-skip` are marked as
  successfully rolled back without CloudFormation touching them — they
  become orphaned (still exist physically but CFN no longer tracks them).

- **Custom resources have a 1-hour CloudFormation timeout, separate
  from the Lambda's own Timeout.** If the Lambda times out at 3s,
  CloudFormation still waits the full hour before failing. Always check
  both the Lambda's Timeout and the CFN event timestamp.

- **Nested stacks are independent stacks.** A child in
  `UPDATE_ROLLBACK_FAILED` must be fixed with its own
  `continue-update-rollback` before the parent can retry.

- **`DeletionPolicy: Retain` and `UpdateReplacePolicy` change rollback
  behaviour.** `Retain` prevents resource deletion during rollback
  (resource may be orphaned). `UpdateReplacePolicy` controls what
  happens to the old resource during a replacement-driven update.

- **Drift detection must be initiated manually.** CloudFormation does
  not continuously monitor drift. Always run `detect-stack-drift` then
  `describe-stack-resource-drifts` proactively during rollback diagnosis.

- **ChangeSet is the safe preview before a rollback retry.** Creating a
  ChangeSet with the previous template shows exactly which resources
  will change (Add/Modify/Remove) before executing — especially useful
  for IAM replacement or dependent resource scenarios.

- **`DisableRollback: true` means CloudFormation did NOT roll back.**
  The stack stays post-failure with successfully-created resources in
  place. The operator must manually clean up or fix the stack.
