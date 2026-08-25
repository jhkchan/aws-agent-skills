---
name: backup-vault-compliance-automator
description: Designs and implements AWS Backup vault compliance automation workflows. Enforces vault policies (deny non-encrypted backups), validates vault lock compliance (governance vs compliance mode), automates backup report generation (daily compliance summary), verifies recovery point encryption, audits backup plan coverage (identifies resources without backup plans), validates cross-region backup replication, checks backup frequency compliance (daily for production), enforces retention policy, manages Vault Lock cool-off periods, deploys multi-account compliance via AWS Organizations, and wires Config rules for continuous backup compliance detection. Emits AUTOMATION_DEPLOYED with deployment templates or REVIEW_REQUIRED with the specific gap. Use when enforcing backup vault security, auditing backup coverage, deploying Vault Lock, verifying cross-region replication, or building Config-based backup compliance monitoring.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline workflow design. Live deployment uses aws backup create-backup-vault, put-backup-vault-policy, put-backup-vault-lock-configuration, describe-backup-vault, list-recovery-points-by-backup-vault, start-backup-job, describe-backup-job, create-backup-plan, create-backup-selection, create-framework, describe-framework, aws configservice put-config-rule, put-remediation-configurations...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Storage
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
  when_to_use: Enforcing backup vault security policies, deploying Vault Lock (governance or compliance mode), auditing backup plan coverage across resources, verifying recovery point encryption, validating cross-region replication, checking backup frequency compliance, deploying Config rules for backup governance, automating backup compliance reports, or rolling out multi-account backup compliance via AWS Organizations.
  activation_triggers: enforce backup vault policy, deploy vault lock, backup coverage audit, recovery point encryption verification, cross-region backup compliance, backup frequency check, Config rule for backup compliance, backup compliance report, multi-account backup governance, governance mode vault lock, compliance mode vault lock, backup plan coverage audit
  invocation_schema: 'Input: either (a) a backup vault configuration (vault name, policy requirements, lock mode) plus target resources, OR (b) a backup compliance requirement ("all production resources must have daily backups with 30-day retention", "verify all recovery points are encrypted"). Output: deterministic COMPLIANCE block per vault — POLICY/LOCK/COVERAGE/REPLICATION/VERDICT — where VERDICT is AUTOMATION_DEPLOYED (templates ready) or REVIEW_REQUIRED (specific gap cited).'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: AWS Backup, backup vault, vault lock, vault policy, backup compliance, recovery point encryption, backup plan coverage, cross-region backup, backup frequency, retention policy, governance mode, compliance mode, AWS Config rules, backup reports, multi-account backup, AWS Organizations, backup framework, cool-off period
  tags: aws-backup, vault-lock, backup-compliance, vault-policy, cross-region, config-rules, automate
---

# Backup Vault Compliance Automator

## Mindset

**One-line takeaway:** AWS Backup vault compliance is a five-layer
model — **policy** (who can write to the vault) → **lock**
(immutability of retention) → **coverage** (are all resources backed
up?) → **encryption** (are recovery points encrypted?) → **replication**
(is cross-region copy verified?). A gap in ANY layer produces silent
non-compliance: the vault looks secure, but backups are missing,
unencrypted, or not replicated.

- **Vault policy** is the access gate. Without a deny-non-encrypted
  policy, any IAM principal with `backup:StartBackupJob` can write
  unencrypted recovery points to the vault.
- **Vault Lock** is the immutability guarantee. Compliance mode means
  NO ONE — not even root — can shorten retention or delete recovery
  points during the lock window. Governance mode allows privileged
  override. Choose wrong and you either lose compliance certification
  (governance) or lose operational flexibility (compliance).
- **Coverage audit** is the blind-spot finder. AWS Backup does not
  natively alert when a new resource (EC2, RDS, DynamoDB) lacks a
  backup plan. Without a coverage audit, new resources silently
  accumulate without backups until someone notices.

## Quick navigation

| You want to... | Go to |
|---|---|
| Enforce vault policy (deny non-encrypted) | Step 2 |
| Deploy Vault Lock (compliance vs governance) | Step 3 (mode matrix) |
| Verify recovery point encryption | Step 4 |
| Audit backup plan coverage | Step 5 |
| Validate cross-region replication | Step 6 |
| Check backup frequency compliance | Step 7 |
| Deploy Config rule for backup compliance | Step 8 |
| Automate backup compliance reports | Step 9 |
| Roll out across Organizations | Step 10 |
| Manage Vault Lock cool-off period | Step 11 |
| Avoid common compliance pitfalls | Anti-Patterns |
| Recent features (Backup Framework, Cross-Account) | Recent AWS features |

## Critical rules at a glance (do NOT bury these)

1. **Vault Lock compliance mode is IRREVERSIBLE.** Once a vault is
   locked in compliance mode, the lock cannot be removed by anyone —
   including the account root user. You cannot shorten the retention
   period, you cannot delete recovery points, you cannot remove the
   lock. The only path is waiting until each recovery point's retention
   expires naturally. Choose compliance mode ONLY when you are certain
   of the retention requirement.

2. **Vault Lock governance mode allows privileged override.** A
   principal with `backup:CancelLegalHold` can remove the lock and
   delete recovery points. Governance mode is for internal policy
   enforcement where operational flexibility is needed. It does NOT
   meet regulatory immutability requirements (SEC 17a-4, CFTC, FINRA).

3. **Recovery point encryption is SEPARATE from vault encryption.**
   The vault has its own KMS encryption (for vault metadata). Each
   recovery point is encrypted with a KMS key specified at backup job
   creation time. A vault policy that does not enforce
   `aws:ResourceTag/x-calculated-integrity` or equivalent does not
   guarantee encrypted recovery points.

4. **Backup plan coverage is NOT automatic.** A backup selection
   targets resources by tags or resource IDs. A new resource without
   the matching tag or explicit ID is NOT backed up. There is no
   "backup all resources" option — coverage gaps are silent.

5. **Cross-region replication is a COPY, not a separate backup.** The
   replication is asynchronous and may lag behind the primary region.
   A backup job that succeeds in the primary region may not yet be
   replicated to the secondary region. Compliance verification must
   check the COPY status, not just the original job status.

## Pre-flight: data requirements

Designing a backup vault compliance workflow requires these inputs:

| Input | Source | Why |
|---|---|---|
| All backup vaults | `list-backup-vaults` | Inventory of vaults to assess |
| Vault policies | `get-backup-vault-policy` | Current access controls |
| Vault lock configuration | `describe-backup-vault` (LockState) | Whether lock is active and in what mode |
| Recovery points per vault | `list-recovery-points-by-backup-vault` | Encryption status and retention |
| Backup plans and selections | `list-backup-plans`, `list-backup-selections` | Coverage scope |
| Resources without backup | AWS Config + Backup audit | Coverage gap analysis |
| Cross-region copy jobs | `list-copy-jobs` | Replication status |
| KMS keys for backup | `kms describe-key` | Encryption key inventory |
| Organizations backup config | `organizations list-delegated-administrators` | Multi-account setup |
| Config rules for backup | `describe-config-rules` (backup-related) | Existing compliance monitoring |

**If the input is malformed** (missing vault name, ambiguous lock
mode), emit:

```text
COMPLIANCE: <reference>
VAULT: <name or "account-wide">
VERDICT: ERROR
REASON: Cannot design backup vault compliance — vault inventory and lock-mode requirement are required inputs.
GAP: Run list-backup-vaults and describe-backup-vault, then supply the compliance requirement (regulatory standard, retention period).
```

## Process — Backup vault compliance design (apply in order)

### Step 0: Expert knowledge — non-obvious AWS Backup behaviors

Full catalog: [Advanced patterns](references/advanced-patterns.md) — cool-off semantics, policy-vs-lock, Backup Framework, cross-account prerequisites, job validation, lock-vs-IAM.

### Step 1: Inventory the current backup state

Full inventory commands: [Diagnostic commands](references/diagnostic-commands.md).

### Step 2: Enforce vault policy (deny non-encrypted backups)

Vault policy template that enforces encryption:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyUnencryptedBackups",
      "Effect": "Deny",
      "Principal": {"AWS": "*"},
      "Action": ["backup:StartBackupJob", "backup:CopyIntoBackupVault"],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:ResourceTag/x-calculated-integrity": "ENCRYPTED"
        }
      }
    },
    {
      "Sid": "DenyNonApprovedKMSKey",
      "Effect": "Deny",
      "Principal": {"AWS": "*"},
      "Action": ["backup:StartBackupJob", "backup:CopyIntoBackupVault"],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "kms:ViaService": "backup.us-east-1.amazonaws.com"
        }
      }
    },
    {
      "Sid": "EnforceTLS",
      "Effect": "Deny",
      "Principal": {"AWS": "*"},
      "Action": "backup:*",
      "Resource": "*",
      "Condition": {"Bool": {"aws:SecureTransport": false}}
    }
  ]
}
```

Apply the policy:

```bash
aws backup put-backup-vault-policy \
  --backup-vault-name prod-backup-vault \
  --policy file://vault-policy.json \
  --region us-east-1
```

Cross-account vault policy statement: [Advanced patterns](references/advanced-patterns.md).

### Step 3: Deploy Vault Lock (governance vs compliance mode)

**THIS IS THE MOST CRITICAL DECISION IN BACKUP COMPLIANCE.**

| Dimension | Governance Mode | Compliance Mode |
|---|---|---|
| Immutability | Soft — privileged override | Hard — no override, not even root |
| Lock removal | `CancelLegalHold` by privileged principal | IMPOSSIBLE after cool-off |
| Regulatory compliance | Does NOT meet SEC 17a-4, CFTC, FINRA | Meets SEC 17a-4, CFTC, FINRA |
| Operational risk | Low — can correct mistakes | HIGH — cannot correct mistakes |

Deploy governance mode:

```bash
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name prod-backup-vault \
  --changeable-for-days 3 --min-retention-days 1 --max-retention-days 365
```

Deploy compliance mode:

```bash
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name compliance-vault \
  --changeable-for-days 3 --min-retention-days 90 --max-retention-days 2557 --mode COMPLIANCE
```

**Critical warning:** `ChangeableForDays` sets the cool-off. During
cool-off the lock CAN be removed. After expiry, compliance mode is
PERMANENT. Before deploying: verify retention matches regulatory
requirements, verify vault contains only resources needing immutable
retention, test in non-production first, document lock date.

Verify: `aws backup describe-backup-vault --backup-vault-name <vault>
--query '[LockState,MinRetentionDays,MaxRetentionDays,VaultLockDate]'`

### Step 4: Verify recovery point encryption

For each recovery point, verify encryption key ARN is present and
the key is the approved one:

```bash
aws backup list-recovery-points-by-backup-vault \
  --backup-vault-name prod-backup-vault \
  --output json \
  --region us-east-1
```

Per-recovery-point KMS verification script: [Diagnostic commands](references/diagnostic-commands.md).

If violations are found, the vault policy (Step 2) should prevent
future unencrypted backups. Existing unencrypted recovery points
must be either:
1. Re-backed-up with encryption (if retention allows).
2. Deleted and recreated (if not under Vault Lock).
3. Documented as an exception (if under Vault Lock and cannot be
   deleted).

### Step 5: Audit backup plan coverage

Identify resources that lack backup plans:

Resource enumeration commands (EC2, RDS, DynamoDB, plans): [Diagnostic commands](references/diagnostic-commands.md).

Coverage audit logic: enumerate all EC2/RDS/DynamoDB/EFS resources,
cross-reference against backup plan selections (tag-based and
explicit-ID), and compute the gap. A coverage gap means the resource
has NO backup — typically a P1 finding for production.

**Config rule for coverage detection:**

```bash
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "backup-plan-coverage-check",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "BACKUP_RECOVERY_POINT_MANUAL_DELETION_DISABLED"
    },
    "Scope": {"ComplianceResourceTypes": ["AWS::Backup::BackupPlan"]}
  }' \
  --region us-east-1
```

For custom coverage checks (e.g., "all EC2 instances tagged
Environment=prod must have a backup plan"), a custom Lambda Config
rule is required. See **references/backup-config-rules.md**.

### Step 6: Validate cross-region backup replication

Copy-job and destination-vault verification commands: [Diagnostic commands](references/diagnostic-commands.md).

Replication checklist: copy job `COMPLETED`, destination vault has
recovery points, destination KMS key is region-specific (not source
key ARN), recovery point ARN differs from source.

### Step 7: Check backup frequency compliance

Verify backups run at the required frequency via `list-backup-jobs`.

| Resource tier | Required frequency | Required retention |
|---|---|---|
| Production critical (RPO < 4h) | Every 4 hours | 30 days |
| Production standard (RPO < 24h) | Daily | 30-90 days |
| Staging | Weekly | 14 days |
| Development | On-demand | 7 days |

### Step 8: Deploy Config rules for backup compliance

AWS-managed Config rules for backup:

| Rule | What it checks |
|---|---|
| `backup-plan-frequency` | Backup plans meet minimum frequency |
| `backup-recovery-point-encrypted` | All recovery points are encrypted |
| `backup-recovery-point-manual-deletion-disabled` | Vault Lock prevents manual deletion |
| `backup-vaults-are-encrypted` | All backup vaults use KMS encryption |

```bash
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "backup-recovery-point-encrypted",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "backup-recovery-point-encrypted"
    }
  }' \
  --region us-east-1
```

Custom coverage-rule deploy CLI: [Backup Config rules](references/backup-config-rules.md).

For the full custom Config rule Lambda implementation including tag
extraction, backup plan lookup, and compliance evaluation, see
**references/backup-config-rules.md**.

### Step 9: Automate backup compliance reports

Report-plan setup (daily compliance summary to S3): [Advanced patterns](references/advanced-patterns.md).

### Step 10: Multi-account backup compliance via Organizations

Delegated administrator, org-level backup policy, Config aggregation: [Advanced patterns](references/advanced-patterns.md).

### Step 11: Manage Vault Lock cool-off period

| Phase | Duration | What happens |
|---|---|---|
| Pre-lock | N/A | Vault fully mutable |
| Cool-off | `ChangeableForDays` (min 3) | Lock is `LOCKED` but CAN be removed |
| Post-cool-off | Permanent | Compliance mode: IRREVERSIBLE. Governance: override-capable |

Checklist: set `ChangeableForDays` to minimum (3), document lock date,
verify retention during cool-off, confirm `LockState` post-expiry,
verify `delete-backup-vault-lock-configuration` FAILS after cool-off
in compliance mode.

## Output format

```text
COMPLIANCE: <reference>
VAULT: <name or "account-wide">
POLICY:
  - Vault policy: <deny-non-encrypted | open | custom>
  - KMS enforcement: <approved key ARN>
LOCK:
  - Mode: GOVERNANCE | COMPLIANCE | UNLOCKED
  - MinRetention: <days>
  - MaxRetention: <days>
  - CoolOff: <days remaining or "expired — permanent">
COVERAGE:
  - Total resources: <N>
  - Covered: <N>
  - Gap: <N> resources without backup plan
REPLICATION:
  - Cross-region: <destination region, status>
  - Cross-account: <destination account, status>
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
GAP: <if REVIEW_REQUIRED, the specific missing piece>
TEMPLATE: <CLI snippet or JSON for the compliance configuration>
```

### Worked example — AUTOMATION_DEPLOYED, full compliance vault

```text
COMPLIANCE: prod-backup-compliance-baseline
VAULT: prod-backup-vault
POLICY:
  - Vault policy: deny-non-encrypted, enforce-approved-kms, enforce-tls
  - KMS enforcement: arn:aws:kms:us-east-1:111111111111:key/prod-backup-key
LOCK:
  - Mode: COMPLIANCE
  - MinRetention: 90 days
  - MaxRetention: 2557 days (7 years)
  - CoolOff: expired — permanent lock active
COVERAGE:
  - Total resources: 85 (EC2=40, RDS=15, DynamoDB=20, EFS=10)
  - Covered: 82 (by tag-based backup selection)
  - Gap: 3 EC2 instances without BackupPlan tag
REPLICATION:
  - Cross-region: us-west-2, COMPLETED (last copy verified)
  - Cross-account: N/A (single account)
VERDICT: AUTOMATION_DEPLOYED
GAP: None (3 untagged EC2 instances flagged for tagging, Config rule deployed for continuous coverage check)
TEMPLATE:
  aws backup put-backup-vault-policy --backup-vault-name prod-backup-vault --policy file://vault-policy.json
  aws backup put-backup-vault-lock-configuration --backup-vault-name prod-backup-vault --changeable-for-days 3 --min-retention-days 90 --max-retention-days 2557 --mode COMPLIANCE
  aws configservice put-config-rule --config-rule '{"ConfigRuleName":"backup-recovery-point-encrypted","Source":{"Owner":"AWS","SourceIdentifier":"backup-recovery-point-encrypted"}}'
```

## Anti-Patterns — NEVER do these things

- NEVER deploy compliance-mode Vault Lock without testing in
  governance mode first. Compliance mode is IRREVERSIBLE — a
  misconfigured retention period is a permanent problem.

- NEVER assume governance mode meets regulatory requirements. It
  allows privileged override and does NOT satisfy SEC 17a-4, CFTC
  1.31, or FINRA 4511.

- NEVER leave a backup vault without a policy. The default allows
  any principal with `backup:*` to write unencrypted recovery points.

- NEVER assume all resources are covered by backup plans. A new
  resource without the matching tag is silently excluded. Always
  deploy a coverage audit Config rule.

- NEVER verify cross-region replication by checking only the source
  region. Always verify in the DESTINATION region's vault — the copy
  job may report `COMPLETED` but the recovery point may not be
  visible yet.

- NEVER use the same KMS key for source and destination regions.
  KMS keys are region-specific. Using the source key ARN produces
  `KMSNotFoundException` in the destination.

- NEVER omit `ChangeableForDays` when deploying Vault Lock. Set it
  explicitly and document the cool-off expiry date.

- NEVER confuse vault encryption with recovery point encryption.
  The vault has its own KMS key; each recovery point may use a
  different key. Verify both independently.

- NEVER deploy backup coverage using explicit resource IDs only.
  Use tag-based selections (`ListOfTags`) for dynamic coverage.

- NEVER forget that AWS Backup audit evaluates daily, not real-time.
  For immediate alerting, use EventBridge on `Backup Job State Change`.

- NEVER omit cross-account IAM trust. The destination vault policy
  MUST include `aws:PrincipalAccount` for the source account.

- NEVER assume backup report plans are sufficient for compliance
  evidence. Supplement with CloudTrail queries and Config timeline.

## Pre-flight safety checks (run before applying any vault compliance CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit: `CONFIRM: About to <action> for vault <vault> in account
  <account>. Compliance mode locks are IRREVERSIBLE. Proceed? (yes/no)`

- **Back up the current vault policy** before modifying:
  `aws backup get-backup-vault-policy --backup-vault-name <vault> > backup.json`

- **Before deploying compliance-mode Vault Lock**, test in governance
  mode first: deploy with same parameters, verify retention/policy/
  coverage, simulate recovery point lifecycle (create, verify deletion
  is blocked), then deploy compliance mode.

- **Before enabling cross-region replication**, verify destination
  vault exists with correct policy, destination-region KMS key is
  enabled, and backup plan copy config references correct vault/key.

- **For multi-account backup**, verify delegated administrator is
  configured before deploying org-level policies.

## Appendix A — Vault Lock mode decision tree

```
Is the vault subject to regulatory immutability requirements?
├─ Yes (SEC 17a-4, CFTC, FINRA, HIPAA)
│   └─ COMPLIANCE MODE
│       - MinRetention: per regulatory minimum (e.g., 90d, 2557d)
│       - MaxRetention: per regulatory maximum
│       - ChangeableForDays: 3 (minimum)
│       - COOL-OFF EXPIRY IS PERMANENT — verify all parameters before
│       - Test in non-prod first
└─ No
    └─ Is operational flexibility needed (ability to override)?
        ├─ Yes → GOVERNANCE MODE
        │   - MinRetention: per internal policy
        │   - MaxRetention: per internal policy
        │   - Override requires backup:CancelLegalHold permission
        └─ No → COMPLIANCE MODE (for defense-in-depth)
            - Same as regulatory path
            - Use when the organization wants immutability even without regulatory mandate
```

## References (load on demand)

- [Worked examples](references/worked-examples.md) — full walkthroughs (REVIEW_REQUIRED governance-mode review)
- [Error handling](references/error-handling.md) — vault-policy and cross-region replication error tables and remedies
- [Diagnostic commands](references/diagnostic-commands.md) — inventory, encryption verification, coverage enumeration, copy-job checks
- [Advanced patterns](references/advanced-patterns.md) — non-obvious Backup behaviors, cross-account policy, reports, multi-account rollout, cost reference, recent features
- [Backup Config rules](references/backup-config-rules.md) — managed and custom Config rule implementations
- [Vault Lock modes](references/vault-lock-modes.md) — full governance vs compliance mode reference and cost model

## Domain

AWS CloudOps / Storage — AWS Backup vault compliance automation.

## AWS documentation

- **AWS Backup** — https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html
- **Backup Vault Lock** — https://docs.aws.amazon.com/aws-backup/latest/devguide/vaults.html#vault-lock
- **Backup Vault Policies** — https://docs.aws.amazon.com/aws-backup/latest/devguide/access-control-overview.html
- **AWS Backup Frameworks** — https://docs.aws.amazon.com/aws-backup/latest/devguide/frameworks.html
- **AWS Config Rules for Backup** — https://docs.aws.amazon.com/aws-backup/latest/devguide/monitoring-automated.html
