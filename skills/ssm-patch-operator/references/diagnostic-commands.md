# Diagnostic Commands — ssm-patch-operator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Pagination and live-account pre-flight

**Pagination:** `describe-instance-information` returns 50/page by default
— drain `--next-token` for fleet-wide operations. `describe-patch-states`
paginates at 100/page. `list-compliance-items` paginates similarly.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws ssm describe-instance-information --instance-information-filter-list
   Key=InstanceIds,ValueSet=<id>` — confirm `PingStatus: Active` and
   `LastPingDateTime` < 30 min ago. Capture `PlatformType`, `PlatformName`,
   `PlatformVersion`, `ResourceType`, `IamRoleARN`.
2. `aws ec2 describe-instances --instance-ids <id>` — confirm `State: running`
   and capture the IAM instance profile, VPC, subnet, and tags. Diff against
   SSM's view to find instances that have never appeared in SSM (silent
   coverage gap).
3. `aws ssm describe-patch-baselines --filters Key=OWNER,Values=Self,Key=OPERATING_SYSTEM,Values=<OS>`
   — list custom baselines. Separately fetch AWS-owned:
   `--filters Key=OWNER,Values=AWS`.
4. `aws ssm get-patch-baseline-for-instance --instance-id <id>` — returns the
   *effective* baseline for this instance (resolves default + `Patch Group`
   tag + explicit association). This is the source of truth, not
   `describe-patch-baselines`.
5. `aws ssm describe-patch-states --instance-ids <id>` — last scan timestamp,
   installed/missing counts by severity.
6. `aws ssm list-compliance-items --resource-ids <id> --resource-types ManagedInstance`
   — per-patch compliance rows.
7. `aws ssm describe-instance-associations-status --instance-id <id>` — is
   there a `AWS-ApplyPatchBaseline`/`AWS-RunPatchBaseline` association?
   Which Operation?
8. `aws ssm describe-maintenance-window-executions --window-id <id>` (if a
   maintenance window is the target) — last execution status.
9. (Optional, requires SSM document execution) `aws ssm send-command
   --document-name AWS-RunShellScript --parameters commands=["df -m /",
   "df -m /var"]` — confirm free disk space pre-Install.
