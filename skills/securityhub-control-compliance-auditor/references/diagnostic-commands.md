# Diagnostic Commands — Security Hub Control-Compliance Auditor

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Pre-flight safety checks (run before any remediation)

**Dry-run mode (REQUIRED for batch remediation of >5 resources):** Before
applying any fix in bulk, run an audit-only pass:
1. For CLI commands with native `--dry-run` support (e.g., `aws iam
   simulate-principal-policy`, `aws s3api put-bucket-policy --dry-run`):
   run with `--dry-run` and inspect the output for side-effects.
2. For commands without native dry-run (e.g., `put-public-access-block`,
   `enable-key-rotation`): emit the exact command to stdout prefixed with
   `# DRY-RUN:` and HALT. Require explicit user confirmation
   (`--confirm-execute` flag or interactive "yes") before re-running without
   the prefix.
3. For BatchUpdateFindings: first run with `--note "DRY-RUN: would set
   RESOLVED"` but WITHOUT `--workflow Status=RESOLVED`. Verify the note
   appears, then run the real update.
4. Batch dry-run output must include: the command, the target resource ARN,
   the current state (from pre-flight capture), and the expected post-fix
   state. This allows rollback planning before any state change.

- **Confirm the resource still exists** before applying a fix. A finding may
  reference a deleted resource (Security Hub can lag by up to 24h):
  - S3: `aws s3api head-bucket --bucket <name>`
  - IAM: `aws iam get-role --role-name <name>`
  - EC2: `aws ec2 describe-security-groups --group-ids <sg-id>`
  - CloudTrail: `aws cloudtrail describe-trails --trail-name-list <name>`
  If the resource does not exist, update the finding to ARCHIVED.

- **Capture current state for rollback** before modifying any resource:
  - S3 bucket policy: `aws s3api get-bucket-policy --bucket <name> > backup.json`
  - IAM policy: `aws iam get-policy-version --policy-arn <arn> > backup.json`
  - Security group: `aws ec2 describe-security-groups --group-ids <sg> > backup.json`
  Prefer additive changes (enable BPA) over destructive changes (delete
  policy).

- **Confirm the finding is for the current account/region.** Security Hub
  findings are region-scoped. Verify `--region` matches the finding's `Region`
  field.

- **Verify the delegated administrator scope.** If operating from a member
  account, you may not have permissions to modify resources in another member.
  Check `AwsAccountId`.

- **For CRITICAL findings on trust-boundary resources** (cross-account IAM
  roles, public S3 buckets, KMS keys with wildcard policies), treat as
  incident response — contain first (enable BPA, restrict trust policy), then
  investigate CloudTrail for evidence of exploitation during the exposure
  window.

- **Permission fallback:** if the caller receives `AccessDenied` on the
  remediation command, do NOT silently fail. Check for: (1) an SCP denying
  the action at the OU or account level, (2) a permissions boundary capping
  the role, (3) a service control policy from the management account. Document
  the blocker and escalate to the cloud governance team.

