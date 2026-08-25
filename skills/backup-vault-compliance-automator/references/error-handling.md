# Error Handling — Backup Vault Compliance

Load-on-demand error tables and remedies for the Backup Vault Compliance Automator skill.

## Common vault policy errors (Step 2)

Common policy errors:

| Error | Cause | Fix |
|---|---|---|
| Deny is too broad | `Resource: "*"` blocks all operations | Scope to the specific vault ARN |
| Missing KMS condition | Unencrypted backups still accepted | Add `Null` check on `aws:ResourceTag/x-calculated-integrity` |
| Cross-account block | Destination vault missing source account allow | Add `AllowCrossAccountBackup` statement |
| Root lock conflict | Policy allows delete but Vault Lock prevents it | Policy is moot — lock overrides IAM |

## Common cross-region replication failures (Step 6)

Common failures: `ACCESS_DENIED` (destination vault policy missing
source account), `KMS_NOT_FOUND` (source key is region-specific —
create destination-region key), copy job `FAILED` silently (poll
status; set up CloudWatch alarm).
