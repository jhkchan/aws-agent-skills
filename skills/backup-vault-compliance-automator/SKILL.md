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

These behaviors change the compliance design if ignored:

- **Vault Lock cool-off period is mandatory.** When creating a
  compliance-mode lock, AWS enforces a minimum 3-day cool-off
  (`ChangeableForDays`). During cool-off the lock is removable; after
  expiry it is permanent and irreversible. Compliance mode is NOT
  immediately immutable.

- **A backup vault policy is NOT a vault lock.** The policy controls
  IAM access (who can write/read/delete). The lock controls
  immutability (whether deletion is possible at all). Both are needed
  for full compliance.

- **Backup Framework (2024) provides native compliance reporting.**
  Declarative controls (encryption, frequency, retention) with
  automated evaluation. Reduces need for custom Config rules for
  common checks.

- **Cross-account backup requires destination vault policy to allow
  the source account.** A missing `aws:PrincipalAccount` condition
  is the most common cause of cross-account backup failures.

- **`StartBackupJob` does NOT validate the target vault's encryption
  policy at submission.** The job may be accepted but fail at
  completion. Always poll `describe-backup-job` for final status.

- **Recovery point deletion respects Vault Lock retention.** Calling
  `delete-recovery-point` on a locked recovery point fails with
  `InvalidParameterValueException`. The lock overrides IAM.

- **Tag-based backup selections are dynamic; explicit-ID selections
  are static.** A selection targeting `BackupPlan=prod` auto-includes
  new tagged resources. Explicit resource IDs do NOT auto-include
  new resources.

- **AWS Backup audit evaluates compliance daily, not real-time.** For
  immediate alerting, use EventBridge on `Backup Job State Change`.

### Step 1: Inventory the current backup state

```bash
# Vault inventory (name, encryption, lock state, recovery point count)
aws backup list-backup-vaults --query 'BackupVaultList[*].[BackupVaultName,EncryptionKeyArn,LockState,NumberOfRecoveryPoints]'

# Vault policy and lock state
aws backup get-backup-vault-policy --backup-vault-name <vault>
aws backup describe-backup-vault --backup-vault-name <vault> --query '[LockState,MinRetentionDays,VaultLockDate]'

# Recovery point encryption status
aws backup list-recovery-points-by-backup-vault --backup-vault-name <vault> \
  --query 'RecoveryPoints[*].[RecoveryPointArn,ResourceType,Status,EncryptionKeyArn]'

# Backup plans, selections, and copy jobs
aws backup list-backup-plans --query 'BackupPlansList[*].[BackupPlanId,BackupPlanName]'
aws backup list-backup-selections --backup-plan-id <plan-id>
aws backup list-copy-jobs --by-state COMPLETED
```

Surface in the output: vaults without policies, vaults without locks,
recovery points without encryption, resources without backup selections.

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

For cross-account backup vaults, add a statement allowing the source
account:

```json
{
  "Sid": "AllowCrossAccountBackup",
  "Effect": "Allow",
  "Principal": {"AWS": "arn:aws:iam::222222222222:root"},
  "Action": ["backup:CopyIntoBackupVault", "backup:DescribeRecoveryPoint"],
  "Resource": "*"
}
```

Common policy errors:

| Error | Cause | Fix |
|---|---|---|
| Deny is too broad | `Resource: "*"` blocks all operations | Scope to the specific vault ARN |
| Missing KMS condition | Unencrypted backups still accepted | Add `Null` check on `aws:ResourceTag/x-calculated-integrity` |
| Cross-account block | Destination vault missing source account allow | Add `AllowCrossAccountBackup` statement |
| Root lock conflict | Policy allows delete but Vault Lock prevents it | Policy is moot — lock overrides IAM |

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

Check each recovery point:

```python
import boto3

backup = boto3.client('backup')

def verify_encryption(vault_name, approved_kms_key_arn):
    paginator = backup.get_paginator('list_recovery_points_by_backup_vault')
    violations = []

    for page in paginator.paginate(BackupVaultName=vault_name):
        for rp in page['RecoveryPoints']:
            arn = rp['RecoveryPointArn']
            kms_key = rp.get('EncryptionKeyArn')

            if kms_key is None:
                violations.append(f"UNENCRYPTED: {arn} ({rp['ResourceType']})")
            elif kms_key != approved_kms_key_arn:
                violations.append(f"WRONG_KEY: {arn} uses {kms_key}, expected {approved_kms_key_arn}")

    return violations
```

If violations are found, the vault policy (Step 2) should prevent
future unencrypted backups. Existing unencrypted recovery points
must be either:
1. Re-backed-up with encryption (if retention allows).
2. Deleted and recreated (if not under Vault Lock).
3. Documented as an exception (if under Vault Lock and cannot be
   deleted).

### Step 5: Audit backup plan coverage

Identify resources that lack backup plans:

```bash
# List all EC2 instances
aws ec2 describe-instances \
  --query 'Reservations[*].Instances[*].InstanceId' \
  --output text \
  --region us-east-1

# List all RDS instances
aws rds describe-db-instances \
  --query 'DBInstances[*].DBInstanceIdentifier' \
  --output text \
  --region us-east-1

# List all DynamoDB tables
aws dynamodb list-tables \
  --output text \
  --region us-east-1

# List backup selections
aws backup list-backup-plans \
  --output json \
  --region us-east-1
```

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

```bash
aws backup list-copy-jobs --by-state COMPLETED --output json --region us-east-1
aws backup list-recovery-points-by-backup-vault \
  --backup-vault-name prod-backup-vault-dr --region us-west-2
```

Replication checklist: copy job `COMPLETED`, destination vault has
recovery points, destination KMS key is region-specific (not source
key ARN), recovery point ARN differs from source.

Common failures: `ACCESS_DENIED` (destination vault policy missing
source account), `KMS_NOT_FOUND` (source key is region-specific —
create destination-region key), copy job `FAILED` silently (poll
status; set up CloudWatch alarm).

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

Custom Config rule for backup coverage (detect resources without backup
plans):

```bash
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "custom-ec2-must-have-backup-plan",
    "Source": {
      "Owner": "CUSTOM_LAMBDA",
      "SourceDetails": [{
        "EventSource": "aws.config",
        "MessageType": "ConfigurationItemChangeNotification"
      }],
      "SourceIdentifier": "arn:aws:lambda:us-east-1:111111111111:function:check-ec2-backup-coverage"
    },
    "Scope": {"ComplianceResourceTypes": ["AWS::EC2::Instance"]}
  }' \
  --region us-east-1
```

For the full custom Config rule Lambda implementation including tag
extraction, backup plan lookup, and compliance evaluation, see
**references/backup-config-rules.md**.

### Step 9: Automate backup compliance reports

```bash
aws backup create-report-plan \
  --report-plan-name daily-compliance-summary \
  --report-setting '{"ReportTemplates":["BACKUP_JOB_REPORT","BACKUP_POLICY_REPORT"]}' \
  --report-delivery-config '{"S3BucketName":"com-company-backup-reports","Formats":["CSV","JSON"]}' \
  --region us-east-1
```

Reports are generated daily and delivered to S3. Set up Athena tables
on the S3 output for queryable compliance dashboards.

### Step 10: Multi-account backup compliance via Organizations

1. **Delegated administrator:**
   `aws backup register-delegated-administrator --account-id 111111111111`
2. **Org-level backup policy:** Use AWS Organizations backup policies
   (tag-based) to enforce plans across member accounts.
   `aws organizations create-policy --type BACKUP_POLICY --content file://policy.json`
3. **Config aggregation:** Management account aggregates compliance:
   `aws configservice put-configuration-aggregator --organization-aggregator-source '{"RoleArn":"...","AllAwsRegions":true}'`

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

### Worked example — REVIEW_REQUIRED, governance mode on compliance vault

```text
COMPLIANCE: compliance-vault-review
VAULT: compliance-vault
POLICY:
  - Vault policy: deny-non-encrypted (correct)
  - KMS enforcement: correct approved key
LOCK:
  - Mode: GOVERNANCE (WRONG — regulatory requirement is COMPLIANCE)
  - MinRetention: 30 days (WRONG — minimum should be 90 days)
  - MaxRetention: 365 days (WRONG — should be 2557 days for 7-year compliance)
  - CoolOff: lock removable by privileged principal
COVERAGE:
  - Total resources: 50
  - Covered: 50
  - Gap: 0
REPLICATION:
  - Cross-region: NOT CONFIGURED (required for DR)
VERDICT: REVIEW_REQUIRED
GAP: Vault is in GOVERNANCE mode but regulatory requirement (SEC 17a-4) demands COMPLIANCE mode. MinRetention is 30d but policy requires 90d minimum. Cross-region replication is not configured. These three issues must be resolved before the vault can be certified as compliant. Note: switching from GOVERNANCE to COMPLIANCE mode requires removing the current lock (possible in governance mode) and re-deploying in compliance mode with the correct retention parameters.
TEMPLATE: (deploy after mode and retention parameters are confirmed)
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

## Appendix B — Config rules and cost reference

Managed rules: `backup-plan-frequency`, `backup-recovery-point-encrypted`,
`backup-recovery-point-manual-deletion-disabled`, `backup-vaults-are-encrypted`.
Custom rules: coverage audit, min-retention, cross-region copy. See
**references/backup-config-rules.md** for implementations.

Cost summary: warm storage $0.05/GB-mo, cold $0.0125/GB-mo, cross-region
$0.02/GB, backup job $0.025/GB, restore $0.025/GB. See
**references/vault-lock-modes.md** for the full cost model.

## Recent AWS features (2024-2026)

- **AWS Backup Framework (2024):** Declarative compliance controls
  with automated evaluation. Reduces need for custom Config rules for
  common checks (encryption, frequency, retention). Framework reports
  integrate with AWS Audit Manager.

- **Cross-account backup (2024-2025):** Native support for backing
  up resources from one account to a vault in another account without
  custom IAM roles. Simplifies centralized backup architectures.

- **Backup Vault Lock compliance mode enhancements (2024):** Added
  `MaxRetentionDays` parameter to lock configuration. Previously only
  minimum retention was enforceable — now both bounds are locked.

- **CloudWatch Events for backup state changes (2024-2025):**
  EventBridge events for `Backup Job State Change` and `Copy Job
  State Change`. Enables real-time compliance alerting without waiting
  for daily audit evaluation.

- **AWS Backup for Amazon EBS multi-volume consistent snapshots
  (2025):** Application-consistent backups across multiple EBS volumes
  attached to a single EC2 instance. Improves recovery integrity for
  multi-volume databases.

- **Organizations backup policies (2025-2026):** Tag-based backup
  policy enforcement at the organization level. Member accounts inherit
  backup plans based on resource tags without individual account
  configuration.

- **Backup continuous verification (2025-2026):** Automated restore
  testing — periodically restores recovery points and validates data
  integrity. Catches silent backup corruption that standard job-status
  monitoring misses.

## Expert heuristic: the silent coverage gap

The most dangerous backup compliance failure is a resource that has
NEVER been backed up because no one tagged it for a backup plan.

**The rule (non-negotiable):**

> EVERY production resource MUST be covered by a backup plan. The ONLY
> guarantee against coverage gaps is a Config rule that flags
> resources without backup as NON_COMPLIANT.

**Why:** AWS Backup does not natively alert when a new resource is
created without coverage. An engineer creates a new RDS instance,
forgets to tag it, and it runs without backups for months — typically
discovered during an incident when recovery is needed and impossible.

**Detection:** Custom Config rule on EC2/RDS/DynamoDB evaluating tag
presence; AWS Backup Framework coverage control; EventBridge on
`RunInstances`/`CreateDBInstance` for real-time tag check.

**Surface in output:** include `COVERAGE_GAP: <count>` and
`UNENCRYPTED_RECOVERY_POINTS: <count>`. If either is > 0, do NOT
mark the deployment as complete.

## Domain

AWS CloudOps / Storage — AWS Backup vault compliance automation.

## AWS documentation

- **AWS Backup** — https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html
- **Backup Vault Lock** — https://docs.aws.amazon.com/aws-backup/latest/devguide/vaults.html#vault-lock
- **Backup Vault Policies** — https://docs.aws.amazon.com/aws-backup/latest/devguide/access-control-overview.html
- **AWS Backup Frameworks** — https://docs.aws.amazon.com/aws-backup/latest/devguide/frameworks.html
- **AWS Config Rules for Backup** — https://docs.aws.amazon.com/aws-backup/latest/devguide/monitoring-automated.html
