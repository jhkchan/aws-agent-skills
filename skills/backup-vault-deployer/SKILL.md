---
name: backup-vault-deployer
description: >-
  Provisions AWS Backup vaults with production defaults: vault
  creation (KMS encryption, tags), backup plans (rule-based with
  lifecycle, schedule, cross-region copy), vault lock (governance vs
  compliance mode WORM with MinRetentionDays, MaxRetentionDays,
  ChangeableForDays), vault access policy for cross-account backup,
  backup report plans, continuous vs periodic backups (PITR for
  EC2/RDS/DynamoDB), resource-type coverage
  (EC2/RDS/EFS/DynamoDB/S3/FSx), and Audit Manager integration.
  Emits a READY_TO_DEPLOY checklist with verification commands. Use
  when creating a backup vault, locking a vault for compliance,
  deploying a backup plan with cross-region copy, or setting up
  continuous backups for PITR. Triggers: create backup vault, vault
  lock compliance mode, backup plan deploy, backup policy,
  cross-region backup copy, continuous backup pitr, backup vault
  access policy, backup report plan, aws backup org policy.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with backup, kms,
  iam, s3, and organizations access (and cross-account STS assume-role
  if cross-account backup). Works with Terraform
  aws_backup_vault / aws_backup_vault_lock_configuration /
  aws_backup_plan / aws_backup_selection / aws_backup_framework
  resources and CloudFormation AWS::Backup::Vault / BackupPlan
  templates.
keywords:
  - aws
  - backup
  - backup vault
  - cloudops
  - deploy
  - provisioning
  - vault lock
  - compliance mode
  - governance mode
  - worm
  - backup plan
  - backup policy
  - backup selection
  - cross-region copy
  - cross-account backup
  - continuous backup
  - pitr
  - recovery point
  - kms encryption
  - cold storage
  - lifecycle
  - backup reports
  - audit manager
tags:
  - aws
  - backup
  - storage
  - cloudops
  - deploy
  - backup-vault
  - vault-lock
  - compliance-mode
  - backup-plan
  - cross-region
  - pitr
  - kms
  - worm
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Storage
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - backup
    - storage
    - cloudops
    - deploy
    - backup-vault
    - vault-lock
    - compliance-mode
    - backup-plan
    - cross-region
    - pitr
    - kms
    - worm
  dependencies:
    - aws-orchestrator
  keywords:
    - create backup vault
    - vault lock compliance mode
    - backup plan deploy
    - backup policy
    - cross-region backup copy
    - continuous backup pitr
    - backup vault access policy
    - backup report plan
    - aws backup org policy
    - backup vault kms
  when_to_use: >-
    Invoke when the user wants to create an AWS Backup vault, apply a
    vault lock (governance or compliance mode for WORM), deploy a
    backup plan with lifecycle rules and cross-region copy, configure
    continuous backups for PITR, set up backup report plans, configure
    a vault access policy for cross-account backup, or deploy an org-
    level backup policy. Do NOT invoke for operating existing backup
    vault lifecycles (use backup-vault-operator), restoring from
    backups (use backup restore skills), or auditing existing backup
    plans (use backup-plan-auditor).
---

# Backup Vault Deployer

An AWS CloudOps agent skill that provisions AWS Backup vaults and
plans with correct production defaults. The skill walks the operator
through vault creation (KMS encryption, tags), vault lock mode
selection (governance vs compliance), backup plan authoring (rules
with lifecycle, schedule, copy-to-region), backup selections,
continuous vs periodic backup, vault access policy, backup report
plans, and Audit Manager integration — then emits a READY_TO_DEPLOY
checklist with verification commands.

## Activation keywords

create backup vault, vault lock compliance mode, backup plan deploy,
backup policy, cross-region backup copy, continuous backup PITR,
backup vault access policy, backup report plan, AWS Backup org policy,
backup vault KMS.

## STRICT output contract

When this skill is invoked with a backup-vault-provisioning request,
the agent MUST respond with the READY_TO_DEPLOY checklist defined in
the "Output format" section using the literal all-caps labels
`BACKUP_VAULT:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation marked `[✗]`, and `READY_TO_DEPLOY`
MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Vault creation (KMS, tags) | Core vault provisioning |
| Step 2 — Vault lock (governance vs compliance) | WORM / immutability |
| Step 3 — Backup plans (rules, lifecycle, schedule) | Scheduling + retention |
| Step 4 — Cross-region and cross-account copy | DR + cross-account |
| Step 5 — Backup selections | What to back up |
| Step 6 — Continuous vs periodic backups (PITR) | Point-in-time recovery |
| Step 7 — Resource-type coverage | EC2/RDS/EFS/DynamoDB/S3 |
| Step 8 — Vault access policy | Cross-account IAM |
| Step 9 — Backup report plans + Audit Manager | Compliance reporting |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/vault-lock-and-compliance-guide.md | Vault lock detail |
| references/cross-region-and-backup-plans.md | Cross-region + plan detail |

## Mindset

**One-line takeaway:** An AWS Backup vault is the container for
recovery points, encrypted with a KMS key, optionally locked for WORM
immutability. Backup plans define rules (schedule, lifecycle, cross-
region copy). Continuous backups enable PITR for supported resources.

Three misconceptions dominate backup-vault misdesign:

- **"Governance mode is the same as compliance mode."** It is NOT.
  Governance mode allows privileged users to remove the lock and delete
  early. Compliance mode is IRREVOCABLE — no user (including root) can
  delete recovery points before MinRetentionDays expires. For regulatory
  compliance (CIS, NIST, SEC 17a-4), compliance mode is REQUIRED.

- **"A backup plan with a schedule is enough."** It is NOT. The plan
  defines rules, but backup selections determine WHICH resources are
  backed up. A plan with no selections backs up nothing. Tag-based
  selection with inconsistent tagging silently excludes resources.

- **"Cross-region copy is just another rule."** The rule exists, but
  cross-region copy requires the destination vault and KMS key to
  exist. Cross-account copy additionally requires a vault access policy
  on the destination. Without these, the copy fails silently.

## Configuration dependency graph (novel heuristic)

| Configuration | Hard dependencies | Silent failure / immutability | Enables |
|---|---|---|---|
| KMS key | Must exist and be enabled in same Region | Key policy must allow `backup.amazonaws.com` — missing = vault creates but backups fail to encrypt | vault creation |
| Backup vault | KMS key ARN known; name unique per acct+Region | Name is immutable; deletion requires empty vault | recovery points, lock, plans |
| Vault lock (governance) | Vault exists | CAN be removed by privileged users — soft protection only | accidental-deletion resistance |
| Vault lock (compliance) | Vault exists | IRREVOCABLE after ChangeableForDays grace period — no user can remove | regulatory WORM |
| Backup plan | Vault exists (referenced by name) | Plan with rules but no selection backs up nothing | scheduled jobs |
| Backup selection | Plan exists | Tag-based with inconsistent tags silently excludes resources | determines what gets backed up |
| Cross-region copy | Destination vault + KMS key in target Region | Copy without destination = fails silently; backup succeeds but copy never completes | cross-region DR |
| Cross-account copy | Destination vault access policy + KMS key policy grant source acct | Without policies, copy fails with AccessDenied | cross-account backup |
| Continuous backup (PITR) | Rule has `EnableContinuousBackup: true`; resource supports PITR | Periodic backup does NOT enable PITR even if frequent | point-in-time recovery |

**The vault-lock-mode row is the one a baseline model misses.**
Governance and compliance modes look similar in the API but have
fundamentally different immutability guarantees. Choosing governance
for a regulatory requirement is a compliance violation.

## Expert heuristic: vault lock immutability — governance vs compliance

```text
GOVERNANCE MODE (soft lock):
  ├── Privileged users CAN remove the lock and delete early
  ├── Use case: prevent accidental deletion by most operators
  └── NOT suitable for: regulatory compliance (CIS, NIST, SEC 17a-4)

COMPLIANCE MODE (hard lock, WORM):
  ├── NO user can remove the lock (including root) after grace period
  ├── Grace period: ChangeableForDays (default 3) — can modify during this window
  ├── After grace: IRREVOCABLE — lock cannot be removed or modified
  ├── Use case: regulatory compliance, anti-ransomware immutability
  └── REQUIRED for: SEC Rule 17a-4, CFTC, FINRA, HIPAA audit trails

Retention window (both modes):
  MinRetentionDays ≤ DeleteAfterDays ≤ MaxRetentionDays for ALL rules targeting vault
  A rule outside this window causes backup jobs to FAIL.
```

**Key implication:** the #1 vault-lock mistake is choosing governance
mode when compliance mode is required. Always map the regulatory
requirement to the lock mode BEFORE provisioning.

## Expert heuristic: cross-region copy prerequisites

```text
Cross-region copy prerequisites (ALL must be met):
  1. Destination vault exists in target Region
  2. Destination KMS key exists, policy grants source account
  3. Backup plan rule has CopyActions block
  4. (Cross-account) Destination vault access policy grants backup:CopyIntoBackupVault

Copy concurrency: 6 concurrent copy jobs per account+Region (soft limit)
Copy failure does NOT fail the source backup — it fails silently.
The DR vault is empty and nobody knows until a DR test fails.
```

**Key implication:** the #1 cross-region copy mistake is creating the
copy rule without provisioning destination prerequisites. The source
backup succeeds, the copy fails silently, the DR vault is empty.

## Prerequisites (verify before provisioning)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| KMS key exists and enabled | Vault encryption requires a key | `aws kms describe-key --key-id <key-id>` |
| KMS key policy grants backup service | Vault needs to encrypt/decrypt | `aws kms get-key-policy --key-id <key-id>` |
| Vault name not in use | Names unique per account+Region | `aws backup list-backup-vaults` |
| Destination vault exists (if cross-region) | Copy rule references destination by ARN | `aws backup list-backup-vaults --region <dest>` |
| Destination KMS key accessible (if cross-region) | Copy needs destination key | Verify key policy grants source account |
| Vault lock mode decided | Governance vs compliance has different implications | Assess regulatory requirements |
| Retention window decided | Min/Max retention must be known before lock | Assess compliance + business needs |
| Resource tags consistent (if tag-based selection) | Inconsistent tags silently exclude resources | `aws resourcegroupstaggingapi get-resources` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`.

## Step 1 — Vault creation (KMS, tags)

| Parameter | Default | Why |
|---|---|---|
| `BackupVaultName` | Required — unique per account+Region | Identifies the vault |
| `EncryptionKeyArn` | Customer-managed KMS key (NOT AWS-managed) | Allows key policy control, rotation, cross-account |
| `Tags` | Environment, Compliance, DataClass | Cost allocation and governance |

```bash
VAULT_NAME="production-backup-vault"
aws backup create-backup-vault \
  --backup-vault-name "$VAULT_NAME" \
  --encryption-key-arn "$(aws kms describe-key --key-id alias/backup-encryption-key --query 'KeyMetadata.Arn' --output text)" \
  --region us-east-1 \
  --tags Environment=production,Compliance=PCI-DSS
```

**Common mistake:** using the AWS-managed key (`aws/backup`). Its policy
cannot be customized — cross-account backup is impossible. Always use a
customer-managed key for production vaults.

## Step 2 — Vault lock (governance vs compliance)

| Mode | Mutability | Use case | Regulatory suitability |
|---|---|---|---|
| Governance | Lock can be removed by privileged users | Accidental deletion prevention | NOT for compliance |
| Compliance | IRREVOCABLE after grace period | Regulatory immutability | REQUIRED for CIS, NIST, SEC 17a-4 |

```bash
# Compliance mode (irrevocable after 3-day grace period)
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name "$VAULT_NAME" --region us-east-1 \
  --min-retention-days 90 --max-retention-days 365 \
  --changeable-for-days 3 --mode COMPLIANCE
```

**Critical:** compliance mode is irrevocable after ChangeableForDays.
Verify the retention window is correct before the grace period expires.
No user, including root, can remove or modify the lock afterward.

## Step 3 — Backup plans (rules, lifecycle, schedule)

```json
{
  "BackupPlanName": "production-daily-backup",
  "Rules": [{
    "RuleName": "daily-full-backup",
    "TargetBackupVaultName": "production-backup-vault",
    "ScheduleExpression": "cron(0 5 ? * MON-SAT *)",
    "StartWindowMinutes": 480,
    "CompletionWindowMinutes": 10080,
    "Lifecycle": { "DeleteAfterDays": 180, "MoveToColdStorageAfterDays": 60 },
    "EnableContinuousBackup": true
  }]
}
```

| Rule attribute | Healthy | Gap |
|---|---|---|
| `ScheduleExpression` | cron with explicit schedule | Missing → no backups |
| `Lifecycle.DeleteAfterDays` | Within vault lock window | Outside window → job FAILS |
| `Lifecycle.MoveToColdStorageAfterDays` | Before DeleteAfterDays | After Delete → invalid |
| `EnableContinuousBackup` | true for PITR resources | false → no PITR |

**Common mistake:** `DeleteAfterDays=7` with vault lock
`MinRetentionDays=90`. The backup job creates the recovery point but
the lifecycle violates the lock — the job fails.

## Step 4 — Cross-region and cross-account copy

```json
{
  "RuleName": "daily-backup-with-dr-copy",
  "TargetBackupVaultName": "production-backup-vault",
  "ScheduleExpression": "cron(0 5 ? * MON-SAT *)",
  "CopyActions": [{
    "DestinationBackupVaultArn": "arn:aws:backup:us-west-2:123456789012:backup-vault:dr-vault",
    "Lifecycle": { "DeleteAfterDays": 180 }
  }]
}
```

**Cross-account prerequisites (ALL required):**
1. Destination vault exists in target account+Region
2. Destination KMS key policy grants source account:
   `kms:Encrypt`, `kms:GenerateDataKey`
3. Destination vault access policy grants source account:
   `backup:CopyIntoBackupVault`

```bash
# Destination vault access policy (cross-account)
aws backup put-backup-vault-access-policy \
  --backup-vault-name "dr-vault" --region us-west-2 \
  --policy '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::111111111111:root"},"Action":"backup:CopyIntoBackupVault","Resource":"*"}]}'
```

**Critical:** without both the vault access policy AND KMS key policy,
cross-account copy fails with `AccessDenied`. The source backup
succeeds but the copy never completes.

## Step 5 — Backup selections (tag, resource, conditions)

| Method | How | Best for |
|---|---|---|
| Tag-based | `Conditions: { StringEquals: { "aws:ResourceTag/Backup": "daily" } }` | Scalable with tagging |
| Resource ARN | `Resources: ["arn:aws:ec2:...:instance/i-xxx"]` | Specific resources |
| Conditions | `ListOfTags` / `Conditions` with `StringEquals`, `StringLike` | Dynamic inclusion |

```bash
aws backup create-backup-selection \
  --backup-plan-id "$PLAN_ID" --region us-east-1 \
  --backup-selection '{
    "SelectionName": "production-tagged",
    "IamRoleArn": "arn:aws:iam::123456789012:role/service-role/AWSBackupDefaultServiceRole",
    "Conditions": { "StringEquals": { "aws:ResourceTag/Backup": "daily" } }
  }'
```

**Common mistake:** tag-based selection where only 30% of resources have
the expected tag. The plan runs, backs up 30%, and reports success.
Always verify tag coverage before relying on tag-based selection.

## Step 6 — Continuous vs periodic backups (PITR)

| Resource type | PITR support | Granularity |
|---|---|---|
| EC2 | Yes (VSS-enabled) | 1 second (5-min non-VSS) |
| RDS | Yes | 5 minutes |
| DynamoDB | Yes | 1 second |
| EFS | Yes | 15 minutes |
| S3 | No (periodic only) | N/A |
| FSx | No (periodic only) | N/A |

**Common mistake:** a rule with hourly schedule and
`EnableContinuousBackup: false`. This gives periodic backups — NOT PITR.
PITR requires `EnableContinuousBackup: true` (or
`RecoveryPointType: CONTINUOUS` in JSON), enabling continuous
journaling independent of the schedule.

## Step 7 — Resource-type coverage

| Resource | PITR | Cross-region | Notes |
|---|---|---|---|
| EC2 | Yes | Yes | VSS for consistent snapshots |
| RDS | Yes | Yes | Automated + manual backups |
| EFS | Yes | Yes | Incremental backup |
| DynamoDB | Yes | Yes | Continuous + on-demand |
| S3 | No | Yes | Versioning + inventory backup |
| FSx | No | Yes | Lustre, Windows, ONTAP, OpenZFS |

```bash
aws backup list-protected-resources --region us-east-1 \
  --query 'Results[*].{Type:ResourceType,ARN:ResourceArn,LastBackup:LastBackupTime}' --output table
```

**Common mistake:** assuming the plan covers ALL resource types. A
tag-based selection only covers resources with that tag — if EC2
instances are tagged but RDS is not, RDS is silently excluded.

## Step 8 — Vault access policy

```bash
aws backup put-backup-vault-access-policy \
  --backup-vault-name "$VAULT_NAME" --region us-east-1 \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": { "AWS": "arn:aws:iam::111111111111:root" },
        "Action": ["backup:CopyIntoBackupVault","backup:DescribeBackupVault"],
        "Resource": "*"
      },
      {
        "Effect": "Deny",
        "NotPrincipal": { "AWS": "arn:aws:iam::123456789012:root" },
        "Action": "backup:DeleteRecoveryPoint",
        "Resource": "*",
        "Condition": { "StringNotEquals": { "aws:SourceAccount": "123456789012" } }
      }
    ]
  }'
```

**Critical:** a vault access policy allowing `backup:DeleteRecoveryPoint`
from any account is a ransomware vector. Always DENY delete from
external accounts. Vault lock (compliance mode) provides defense-in-depth.

## Step 9 — Backup report plans and Audit Manager

```bash
aws backup create-report-plan \
  --report-plan-name "compliance-report" \
  --report-setting '{"ReportTemplate":"BACKUP_JOB_REPORT"}' \
  --report-delivery-config '{"S3BucketName":"backup-reports","Formats":["CSV","JSON"]}' \
  --region us-east-1
```

| Report template | Content |
|---|---|
| `BACKUP_JOB_REPORT` | Job status, duration, resource |
| `COPY_JOB_REPORT` | Cross-region copy status |
| `RESTORE_JOB_REPORT` | Restore job status |
| `RECOVERY_POINT_REPORT` | Recovery point inventory |

Audit Manager integration feeds backup vault configurations and recovery
points as evidence for compliance assessments (HIPAA, PCI-DSS).

## Recent features

- **Continuous backups for EC2 PITR (2023-2024):** VSS-enabled continuous
  backups with 1-second granularity for EC2.
- **AWS Backup for Amazon S3 (2023-2024):** Periodic snapshot-based
  backup of S3 objects.
- **Backup Search (2024-2025):** Search across recovery points for
  specific files without full restore.
- **Restore testing (2024-2025):** Automated restore testing validates
  recovery points are restorable on a schedule.
- **Logically Air-Gapped Backups (2025-2026):** Vaults isolated from the
  source account's IAM context for enhanced ransomware resistance.
- **FSx for OpenZFS support (2024-2025):** Completing the FSx family.

## NEVER do these things

1. **NEVER use the AWS-managed KMS key (aws/backup) for production.**
   Its policy cannot be customized — cross-account backup, granular key
   policies, and CloudTrail key usage are impossible. Always use a
   customer-managed key.

2. **NEVER choose governance mode for a regulatory compliance
   requirement.** Governance mode allows privileged users to remove the
   lock. For CIS 3.6, NIST CP-9, SEC Rule 17a-4, compliance mode is
   REQUIRED.

3. **NEVER apply compliance-mode vault lock without verifying the
   retention window.** Compliance mode is IRREVOCABLE after
   ChangeableForDays. If Min/Max retention is wrong, it cannot be fixed.

4. **NEVER create a backup plan rule with lifecycle outside the vault
   lock window.** DeleteAfterDays below MinRetentionDays or above
   MaxRetentionDays causes the backup job to FAIL.

5. **NEVER assume a backup plan with rules but no selections backs up
   anything.** Selections determine WHAT gets backed up. Always verify
   selections exist and match the intended resource set.

6. **NEVER create a cross-region copy rule without provisioning the
   destination vault and KMS key first.** The source backup succeeds but
   the copy fails silently — the DR vault is empty.

7. **NEVER use tag-based backup selection without verifying tag
   coverage.** Inconsistent tagging silently excludes resources.

8. **NEVER allow `backup:DeleteRecoveryPoint` from external accounts in
   the vault access policy.** This is a ransomware vector. Always DENY
   delete from non-owner accounts.

9. **NEVER assume periodic backups provide PITR.** PITR requires
   `EnableContinuousBackup: true`. A rule with SNAPSHOT only, even if
   hourly, does NOT enable point-in-time recovery.

10. **NEVER forget to test restores.** Use restore testing (2024-2025
    feature) or schedule periodic manual restore drills.

## Output format

```text
BACKUP_VAULT: <vault-name> (<region>) — KMS: <key-id>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Vault name: <name> (unique per account+Region)
  [✓|✗] KMS key: <key-arn> (customer-managed, enabled)
  [✓|✗] KMS key policy: backup service principal granted
  [✓|✗] Tags: <key=value list>
  [✓|✗] Vault lock: Governance | Compliance | None
  [✓|✗] Lock retention: MinRetentionDays=<n>, MaxRetentionDays=<n>
  [✓|✗] Lock grace period: ChangeableForDays=<n>
  [✓|✗] Backup plan: <plan-name> (<rule-count> rules)
  [✓|✗] Plan schedule: <cron-expression>
  [✓|✗] Lifecycle: DeleteAfterDays=<n>, MoveToColdAfterDays=<n>
  [✓|✗] Lifecycle within lock window: PASS | FAIL
  [✓|✗] Continuous backup (PITR): enabled | periodic-only
  [✓|✗] Backup selection: tag-based | resource-ARN (<resource-count> resources)
  [✓|✗] Cross-region copy: destination vault <name> in <region> (ready | missing)
  [✓|✗] Cross-account: vault access policy configured | N/A
  [✓|✗] Vault access policy: delete denied from external accounts
  [✓|✗] Report plan: <name> → S3 bucket <bucket>
VERIFICATION_COMMANDS:
  aws backup describe-backup-vault --backup-vault-name <name> --region <region>
  aws backup list-backup-plans --region <region>
  aws backup list-backup-selections --backup-plan-id <plan-id> --region <region>
  aws backup list-protected-resources --region <region>
```

### Worked example — compliance-mode vault with cross-region DR

```text
BACKUP_VAULT: production-backup-vault (us-east-1) — KMS: alias/backup-encryption-key
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Vault name: production-backup-vault (unique)
  [✓] KMS key: arn:aws:kms:us-east-1:123456789012:key/abcd1234 (customer-managed, enabled)
  [✓] Tags: Environment=production, Compliance=PCI-DSS
  [✓] Vault lock: Compliance
  [✓] Lock retention: MinRetentionDays=90, MaxRetentionDays=365
  [✓] Lock grace period: ChangeableForDays=3 (verify before expiry)
  [✓] Backup plan: production-daily-backup (3 rules)
  [✓] Plan schedule: cron(0 5 ? * MON-SAT *)
  [✓] Lifecycle: DeleteAfterDays=180, MoveToColdAfterDays=60
  [✓] Lifecycle within lock window: PASS (90 ≤ 180 ≤ 365)
  [✓] Continuous backup (PITR): enabled (RDS, DynamoDB)
  [✓] Backup selection: tag-based (Backup=daily) — 45 resources matched
  [✓] Cross-region copy: destination vault dr-backup-vault in us-west-2 (ready)
  [✓] Cross-account: N/A (same-account cross-region)
  [✓] Vault access policy: delete denied from external accounts
  [✓] Report plan: compliance-report → S3 backup-reports
VERIFICATION_COMMANDS:
  aws backup describe-backup-vault --backup-vault-name production-backup-vault --region us-east-1
  aws backup list-backup-plans --region us-east-1
  aws backup list-backup-selections --backup-plan-id <plan-id> --region us-east-1
  aws backup list-protected-resources --region us-east-1
```

## Domain

AWS CloudOps / AWS Backup Vault Provisioning & Backup Plan Deployment.

## AWS documentation

- **AWS Backup Developer Guide** — https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html
- **Backup vaults** — https://docs.aws.amazon.com/aws-backup/latest/devguide/vaults.html
- **Vault lock** — https://docs.aws.amazon.com/aws-backup/latest/devguide/vaults-locking.html
- **Backup plans** — https://docs.aws.amazon.com/aws-backup/latest/devguide/about-backup-plans.html
- **Cross-region backup** — https://docs.aws.amazon.com/aws-backup/latest/devguide/cross-region-backup.html
- **Cross-account backup** — https://docs.aws.amazon.com/aws-backup/latest/devguide/cross-account-backup.html
- **Continuous backups (PITR)** — https://docs.aws.amazon.com/aws-backup/latest/devguide/point-in-time-recovery.html
- **Backup reports** — https://docs.aws.amazon.com/aws-backup/latest/devguide/backup-reports.html
