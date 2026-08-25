# Diagnostic and pre-flight commands — networkmanager-core-network-auditor

Pre-flight safety gates and command listings moved verbatim from SKILL.md (load on demand).

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (PutResourcePolicy, ExecuteCoreNetworkChangeSet, UpdateAttachment,
  DeleteAttachment), the auditor MUST emit:
  `CONFIRM: About to <action> on core network <id> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`

- **Policy backup.** Capture the current LIVE policy before any
  modification:
  `aws networkmanager get-core-network-policy --core-network-id <id> --policy-version LIVE --output json > /tmp/<id>-policy-backup-$(date +%s).json`.
  Core network policies support rollback to prior generations, but the
  backup is the safety net if the rollback itself fails.

- **Verify attachment dependencies before deletion.** Before recommending
  attachment removal, check `aws ec2 describe-subnets --filters
  Name=vpc-id,Values=<vpc-id>` and confirm no production workloads
  depend on the VPC's core network connectivity.

- Prefer additive changes (restrict a policy, add a condition) over
  destructive changes (delete an attachment, remove a segment). Additive
  changes are reversible; attachment deletion is an immediate outage.
