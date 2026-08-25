# Diagnostic Commands (load on demand) — DR Failover Automator

Live-account pre-flight checks and pre-failover safety checks, moved verbatim from SKILL.md.


---

## Live-account pre-flight checks (skip for offline authoring) (moved from SKILL.md)

1. Verify Route 53 hosted zone exists: `aws route53 list-hosted-zones`.
2. Verify secondary region enabled: `aws account get-region-opt-status --region-name <secondary>`.
3. Verify Aurora Global cluster (if applicable): `aws rds describe-global-clusters`.
4. Verify Elastic DRS source servers synced: `aws drs describe-source-servers`.
5. Verify AWS Backup vault in secondary region: `aws backup list-backup-vaults --region <secondary>`.

## Pre-flight safety checks (moved from SKILL.md)


- **MANDATORY CONFIRMATION GATE.** Before any state-changing DR operation
  (`rds failover-global-cluster`, `drs start-recovery`, `route53
  change-resource-record-sets` for failover), emit:
  `CONFIRM: About to <action> for <component> from <primary> to
  <secondary>. Proceed? (yes/no)` and wait for explicit `yes`.
- **Dry-run with `is_drill=true`.** DRS supports drill mode; Aurora
  Global supports managed planned failover. Always drill before going
  live with the orchestrator.
- **Verify the kill-switch is enabled.**
  `aws ssm get-parameter --name /dr/kill-switch` should return `enabled`.
- **Verify health check endpoints respond 200 in both regions.**
- **Verify the rollback path.** Aurora Global reverse requires snapshot
  rebuild; RDS requires re-snapshot. Plan ahead.
- **Verify the on-call notification path.** Send a test SNS message —
  unconfirmed subscriptions silently drop notifications.