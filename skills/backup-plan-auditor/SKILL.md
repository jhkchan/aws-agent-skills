---
name: backup-plan-auditor
description: >-
  Audits AWS Backup plans for coverage gaps (empty or missing resource
  selections), vault risks (missing vault lock, governance-mode lock,
  AWS-managed encryption key), impossible lifecycle configurations (cold
  storage transition at or after deletion, retention below vault-lock floor),
  and compliance violations (backup frequency below daily, retention below
  30 days). Emits a deterministic verdict (COVERAGE_GAP | VAULT_RISK |
  NONCOMPLIANT | CONFIG_GAP | OK) per plan with enumerated findings and
  specific CLI remediation. Use when reviewing backup plans, checking backup
  coverage, auditing vault lock posture, validating lifecycle rules, or
  verifying backup compliance before an audit.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline plan-document classification.
  Live-account audits use aws backup get-backup-plan, aws backup
  list-backup-plans, aws backup describe-backup-vault, and aws backup
  get-backup-vault-access-policy (AWS CLI v2, SSO or key-based credentials).
keywords:
  - AWS Backup
  - backup plan
  - backup vault
  - vault lock
  - coverage gap
  - lifecycle
  - cold storage
  - retention
  - backup frequency
  - compliance
  - ransomware
  - WORM
  - backup audit
  - MoveToColdStorageAfterDays
  - DeleteAfterDays
  - cross-region copy
  - backup selection
  - ScheduleExpression
  - ChangeableForDays
tags: [backup, storage, recovery, vault-lock, lifecycle, compliance, audit, ransomware]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Storage
  verdict_shape: "COVERAGE_GAP | VAULT_RISK | NONCOMPLIANT | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing an AWS Backup plan before production deployment, checking for
    coverage gaps, auditing vault lock posture, validating lifecycle rules,
    verifying backup frequency and retention compliance, or hardening backup
    posture against ransomware.
  activation_triggers:
    - "audit this backup plan"
    - "check backup coverage"
    - "is my backup vault locked"
    - "backup lifecycle invalid"
    - "backup compliance check"
    - "cold storage transition"
    - "vault lock governance vs compliance"
    - "backup retention too short"
    - "ransomware protection backup"
  invocation_schema: >-
    Input: either (a) a backup plan configuration (rules, selections, vault
    metadata), OR (b) a plan-id/ARN for live-account audit. Output:
    deterministic PLAN/VERDICT/REASON/FINDINGS/REMEDIATION block per plan,
    where VERDICT is one of COVERAGE_GAP, VAULT_RISK, NONCOMPLIANT,
    CONFIG_GAP, OK.
---

# Backup Plan Auditor

## Mindset

**One-line takeaway:** the verdict is the **first** classification step that
triggers, evaluated in strict priority order — CONFIG_GAP, then COVERAGE_GAP,
then VAULT_RISK, then NONCOMPLIANT, then OK. A broken lifecycle is a
prerequisite problem; fix it before assessing coverage or compliance.

AWS Backup centralises backups across services, but the plan configuration
is where resilience is built or silently lost. Three failure modes dominate:

- **False sense of coverage** — the plan exists, the vault is locked, the
  schedule runs daily, but the resource selection is empty. Nothing is
  backed up, and nobody notices until a restore fails.
- **Ransomware-vulnerable vault** — backups run correctly, but the vault has
  no lock (or a governance-mode lock bypassable by root). A ransomware
  attacker who compromises the account deletes both data and backups.
- **Impossible lifecycle** — cold storage transition is scheduled at or after
  deletion. The backup is destroyed before it can ever reach cold storage,
  silently defeating the cost-optimisation tier.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| `MoveToColdStorageAfterDays >= DeleteAfterDays` | **CONFIG_GAP** | 1a |
| `DeleteAfterDays < VaultLock.MinRetentionDays` | **CONFIG_GAP** | 1b |
| All selections: `Resources: []` + no tags + no conditions | **COVERAGE_GAP** | 2a |
| Vault lock = NONE | **VAULT_RISK** | 3a |
| Vault lock = GOVERNANCE (`ChangeableForDays > 0`) | **VAULT_RISK** | 3b |
| Vault encryption = `aws/backup` (AWS-managed key) | **VAULT_RISK** | 3c |
| Schedule is sub-daily (weekly/monthly cron) | **NONCOMPLIANT** | 4a |
| `DeleteAfterDays < 30` | **NONCOMPLIANT** | 4b |
| All dimensions pass | **OK** | 5 |

Steps apply in order — the first step that triggers determines the verdict.
See the ordered classification below for edge cases and additive findings.

## Pre-flight: plan and vault metadata gate

Before classification, validate the input structure and identify metadata
that short-circuits the audit.

**Live-account sweep note (pagination):** `aws backup list-backup-plans`
returns at most 100 per page. Use `--next-token` to page through all plans.
For each plan, also page `aws backup list-backup-selections --backup-plan-id
<id>` (100/page) and `aws backup describe-backup-vault --backup-vault-name
<vault>`. Always drain `NextToken` to completion — the long tail of plans
is where stale, uncovered, or misconfigured backups hide.

**If the plan configuration is malformed** (invalid JSON/YAML, missing
required `Rules` or `BackupSelection`), output:

```text
PLAN: <name>
VERDICT: ERROR
REASON: Backup plan configuration is not valid — cannot classify.
REMEDIATION: Retrieve the canonical config with aws backup get-backup-plan
--backup-plan-id <id> --output json and re-audit.
```

## Process — Classification logic (apply in order, first match wins)

### Step 0: Expert knowledge — non-obvious AWS Backup behaviors

These behaviors are easy to misjudge without operational backup experience.
Each changes a verdict if ignored:

- **Cold storage and deletion both count from creation date.** Both
  `MoveToColdStorageAfterDays` and `DeleteAfterDays` count from the
  recovery-point creation timestamp. If cold = 90 and delete = 90, the
  backup is deleted at the exact moment it would transition to cold — the
  cold tier is never used. The strict requirement is
  `MoveToColdStorageAfterDays < DeleteAfterDays` (not equal).

- **Vault lock governance mode is NOT compliance mode.** Governance mode
  (`ChangeableForDays > 0`) is a cooling-off period during which root can
  still modify or remove the lock. Only after `ChangeableForDays` reaches 0
  does the lock become permanent compliance mode. A vault in governance
  mode provides no guarantee against a compromised root account — classify
  as VAULT_RISK.

- **The AWS-managed key `aws/backup` is shared across ALL accounts in the
  region.** You cannot attach a customer key policy, restrict principals, or
  audit access independently. For compliance frameworks requiring CMK
  control (SOC 2, HIPAA, FedRAMP), this is a gap.

- **Vault lock `MinRetentionDays` enforces a retention floor.** A backup
  rule targeting a locked vault MUST have `DeleteAfterDays >=
  MinRetentionDays`. The PutBackupPlan API rejects violations on creation,
  but configs in CloudFormation or IaC templates can contain the violation
  before deployment.

- **Cross-region copy actions have INDEPENDENT vault locks and lifecycles.**
  A CopyAction targets a destination vault in another region — that vault
  has its own lock, encryption key, and retention policy. The source vault's
  lock does NOT protect the copy. Evaluate the destination vault
  independently.

- **Each rule in a plan backs up ALL selected resources independently.** A
  plan with three rules creates three recovery points per resource per run.
  This is a cost multiplier — a common misconfiguration when teams add a
  weekly rule without removing resources from the daily rule.

- **`WindowsVSS: enabled` is required for application-consistent Windows EC2
  backups.** Without it, backups are crash-consistent only. For Windows
  instances running SQL Server or Active Directory, crash-consistent backups
  can produce corrupt database restores.

- **ScheduleExpression uses EventBridge cron syntax.**
  `cron(Min Hour Day-of-month Month Day-of-week Year)`. Day-of-month `*`
  means every day (daily). Day-of-month `?` with a specific Day-of-week
  (e.g., `1` for Monday) means weekly. A specific Day-of-month (e.g., `1`)
  with Day-of-week `?` means monthly. You cannot specify values in BOTH
  Day-of-month and Day-of-week — one must be `?`.

- **Continuous backups (PITR) are separate from periodic snapshots.**
  `EnableContinuousBackup: true` enables point-in-time recovery for RDS and
  DynamoDB with a maximum 35-day window. This supplements but does NOT
  replace periodic snapshots, which can be retained for years. Evaluate
  both independently.

- **Tag-based selection is eventually consistent.** A newly tagged resource
  may take up to 24 hours to be picked up by a tag-based backup selection.
  Do not treat a newly tagged resource as "covered" until the next backup
  window confirms the selection.

- **Legal hold is per-recovery-point and overrides BOTH lifecycle and vault
  lock.** Unlike vault lock (vault-level), legal hold is placed on
  individual recovery points. A recovery point under legal hold cannot be
  deleted even after its `DeleteAfterDays` expires, and even if it exceeds
  the vault's `MaxRetentionDays`. Legal-held recovery points accumulate
  indefinitely until the hold is released — this can cause unexpected
  storage costs and quota exhaustion (each vault supports up to 1,000,000
  recovery points).

- **The default backup vault ("default") ships with NO vault lock and NO
  access policy.** Any principal with broad `backup:*` IAM permissions can
  delete recovery points. This is the most common VAULT_RISK pattern — teams
  use the default vault for convenience and never add a lock. Always flag
  `TargetBackupVault: default` as a VAULT_RISK finding.

- **Updating a backup plan rule is atomic — specifying a partial lifecycle
  clears omitted fields.** If a rule has `MoveToColdStorageAfterDays: 30,
  DeleteAfterDays: 90` and you update it specifying only
  `DeleteAfterDays: 90`, the `MoveToColdStorageAfterDays` is silently set
  to null (cold storage disabled). Always specify the FULL lifecycle object
  on every rule update, not just the changed field.

- **Cross-account backup requires a KMS key policy grant on the destination
  vault's key.** If account A backs up to a vault in account B, account B's
  vault KMS key policy must explicitly allow account A's backup role to
  `kms:Decrypt` and `kms:GenerateDataKey`. Without this, cross-account
  backups fail silently with an encryption error — the job shows as
  `COMPLETED` but the recovery point is unusable for restore.

### Step 1: CONFIG_GAP — invalid or impossible configuration

Check each rule's lifecycle, vault reference, and retention floor. The first
sub-step that triggers produces CONFIG_GAP.

**1a. Impossible lifecycle — cold storage at or after deletion.**
If `MoveToColdStorageAfterDays >= DeleteAfterDays`, the recovery point is
deleted before or at the exact moment it would transition to cold storage.
The cold tier is never used and the cost-optimisation intent is silently
defeated. This is always CONFIG_GAP regardless of other dimensions.

**1b. Retention below vault-lock floor.**
If the vault has a compliance-mode lock with `MinRetentionDays`, and any
rule's `DeleteAfterDays < MinRetentionDays`, the rule violates the lock
floor. The API rejects this on creation, but it can exist in IaC templates
or stale configs. Flag as CONFIG_GAP.

**1c. Missing or invalid TargetBackupVault.**
If a rule references a vault that does not exist in the plan's region, the
rule fails silently — backups are never created.

If none of 1a/1b/1c trigger, proceed to Step 2.

### Step 2: COVERAGE_GAP — resource coverage assessment

**2a. Empty resource selection.**
If ALL backup selections have `Resources: []` AND no `ListOfTags` AND no
`Conditions`, the plan backs up nothing. This is the most dangerous failure
mode — the plan appears healthy (rules, schedules, vault lock all
configured) but protects zero resources. A false sense of security.

**2b. No selections defined.**
If the plan has rules but zero backup selections, no resources are assigned.
Same outcome as 2a.

**2c. Explicit-resource gap (when resource inventory is provided).**
If the input includes a resource inventory (list of production EC2/RDS/DDB
resources), check whether all are covered by at least one selection (by
explicit ARN or matching tag). Flag uncovered critical resources. This
check only fires when an inventory is provided.

If none of 2a/2b/2c trigger, proceed to Step 3.

### Step 3: VAULT_RISK — vault security posture

Evaluate the vault referenced by each rule. The vault is the last line of
defence against ransomware and insider threats.

**3a. No vault lock.**
If the vault has no lock configuration (`Vault lock: NONE`), any principal
with `backup:DeleteRecoveryPoint` can delete backups — including a
compromised role or ransomware attacker with AWS credentials. Zero tamper
protection.

**3b. Governance-mode lock.**
If the vault lock is in governance mode (`ChangeableForDays > 0`), the lock
can still be modified or removed by the root account. A compromised root
can unlock and delete backups. Flag as VAULT_RISK, but note the date when
the lock transitions to compliance mode.

**3c. AWS-managed encryption key.**
If the vault encryption key is `aws/backup` (AWS-managed), the key is shared
across all accounts in the region with no customer-controlled policy.
Additive finding — combine with 3a/3b for the VAULT_RISK verdict, or note
standalone if the lock is already in compliance mode.

If the vault has a compliance-mode lock AND a customer-managed key, the
vault dimension passes. Proceed to Step 4.

### Step 4: NONCOMPLIANT — compliance baseline check

Evaluate backup frequency and retention against the default compliance
baseline. This models common SOC 2 / ISO 27001 / CIS AWS Foundations
requirements. Adjust per-organisation if the input specifies a different
policy.

**Default compliance baseline:**
- Minimum backup frequency: **daily** (RPO of 24 hours)
- Minimum retention: **30 days**

**4a. Sub-daily frequency.**
Parse the `ScheduleExpression` cron. If Day-of-month is NOT `*` (i.e., a
specific day number or `?` with a specific Day-of-week), the schedule is
weekly or monthly — below the daily minimum. Flag as NONCOMPLIANT.

**4b. Insufficient retention.**
If any rule's `DeleteAfterDays < 30`, the retention is below the minimum.
Flag as NONCOMPLIANT.

**4c. No cross-region copy for production (advisory).**
If the selection includes production resources and no `CopyActions` are
defined, add an advisory: no cross-region copy means a single-region
failure makes all backups inaccessible. Advisory only — does not change
the verdict unless 4a/4b also trigger.

If none of 4a/4b trigger, proceed to Step 5.

### Step 5: OK — all dimensions pass

If the plan has valid lifecycle rules (Step 1), covers at least one
resource (Step 2), uses a vault with compliance-mode lock and CMK
encryption (Step 3), and meets the daily + 30-day retention baseline
(Step 4), the plan passes all audit dimensions.

## Output format (per plan)

```text
PLAN: <plan-name>
VERDICT: COVERAGE_GAP | VAULT_RISK | NONCOMPLIANT | CONFIG_GAP | OK
REASON: <1-2 sentences citing the triggering step and finding>
FINDINGS:
  - <finding description (Step Na)>
  - <finding description (Step Nb)>
  - [OK] <dimensions that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — impossible lifecycle

```text
PLAN: cold-storage-backup
VERDICT: CONFIG_GAP
REASON: Rule "efs-cold-tier" has MoveToColdStorageAfterDays (90) >=
DeleteAfterDays (30) — the cold-storage transition can never execute because
the recovery point is deleted first (Step 1a).
FINDINGS:
  - CONFIG_GAP: Impossible lifecycle in rule "efs-cold-tier" — MoveToColdStorageAfterDays 90 >= DeleteAfterDays 30 (Step 1a)
  - [OK] Vault "compliant-vault" has compliance-mode lock and CMK encryption
REMEDIATION:
  1. Set MoveToColdStorageAfterDays to less than DeleteAfterDays
     (e.g., 30 for cold, 90 for delete). Update the rule:
     aws backup update-backup-plan --backup-plan-id <id>
     --backup-plan file://fixed-plan.json
```

## Edge-case handling

- **Plan with multiple rules, some valid, some broken.** Evaluate each rule
  independently for CONFIG_GAP. If ANY rule has an impossible lifecycle, the
  verdict is CONFIG_GAP — one broken rule can cause the entire plan to fail.

- **Selection with both Resources and ListOfTags.** AWS Backup unions these
  — a resource is selected if it matches either the explicit ARNs or the
  tags. An empty `Resources: []` with non-empty `ListOfTags` is NOT a
  coverage gap — the tag-based selection covers resources.

- **Vault lock transition during audit.** If `ChangeableForDays` is between
  0 and 1, the lock is about to transition from governance to compliance.
  Classify as VAULT_RISK (governance) — the transition has not completed.

- **Continuous backup (PITR) enabled.** `EnableContinuousBackup: true`
  provides a 35-day PITR window for RDS/DynamoDB. This supplements but does
  not replace periodic snapshots. Do NOT downgrade a NONCOMPLIANT verdict
  based on PITR alone — periodic snapshot retention must still meet 30 days.

## Anti-Patterns — NEVER

- NEVER classify a plan with `Resources: []` and no tags/conditions as OK.
  The plan backs up nothing — COVERAGE_GAP regardless of how well-configured
  the rules, schedule, and vault are. A healthy-looking plan that protects
  zero resources is worse than no plan (false sense of security).

- NEVER treat governance-mode vault lock (`ChangeableForDays > 0`) as
  equivalent to compliance-mode lock. Governance mode is a cooling-off
  period — root can still remove the lock. A ransomware attacker who
  compromises root can unlock and delete backups. Always VAULT_RISK.

- NEVER classify `MoveToColdStorageAfterDays >= DeleteAfterDays` as OK. The
  cold-storage transition can never execute — the backup is deleted at or
  before the transition moment. Always CONFIG_GAP.

- NEVER treat the AWS-managed key `aws/backup` as equivalent to a
  customer-managed key. The AWS-managed key is shared across all accounts,
  has no customer-controlled policy, and cannot meet CMK-mandated compliance
  requirements.

- NEVER classify a weekly or monthly schedule as OK without a documented
  exception. The default baseline requires daily backups. Flag as
  NONCOMPLIANT against the baseline even if the workload tolerates lower
  frequency — let the operator decide on the exception.

- NEVER assume cross-region copies inherit the source vault's lock. Each
  copy action targets an independent destination vault with its own lock
  configuration. A locked source vault does NOT protect unlocked copies.

- NEVER recommend enabling vault lock without verifying that
  `MinRetentionDays <= plan's shortest rule retention`. Locking a vault
  with MinRetentionDays=90 on a plan with DeleteAfterDays=30 will cause all
  future backups to fail — and the lock is irreversible in compliance mode.

- NEVER assume `Resources: []` with non-empty `ListOfTags` is a coverage
  gap. AWS Backup unions explicit ARNs and tag-based selections — the tags
  cover resources even when Resources is empty.

- NEVER assume tag-based selection provides instant coverage. Tag-based
  selections are eventually consistent — a newly tagged resource may take
  up to 24 hours to be picked up. Do not report a tag-based selection as
  fully covering newly tagged resources until the next backup window
  confirms the selection.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (UpdateBackupPlan, DeleteBackupPlan, PutBackupVaultLockConfiguration),
  emit: `CONFIRM: About to <action> on plan/vault <id>. Proceed? (yes/no)`
  Do NOT execute until the operator confirms.

- Before locking a vault, verify all targeting rules have
  `DeleteAfterDays >= proposed MinRetentionDays`. Locking with a min above
  the plan's retention causes all future backups to fail — and compliance-
  mode lock is irreversible.

- Before modifying a lifecycle, snapshot the current plan:
  `aws backup get-backup-plan --backup-plan-id <id> --output json >
  /tmp/<id>-backup-$(date +%s).json`. Plan updates replace the entire rule
  set — no partial update, no rollback.

## Remediation guidance

### For CONFIG_GAP

1. **Impossible lifecycle:** set `MoveToColdStorageAfterDays` to less than
   `DeleteAfterDays` (e.g., cold at 30, delete at 90). Update via
   `aws backup update-backup-plan --backup-plan-id <id> --backup-plan file://fixed-plan.json`.
2. **Retention below vault floor:** increase `DeleteAfterDays` to >= the
   vault's `MinRetentionDays`, or target a different vault with a lower floor.
3. **Missing vault:** create the vault or update the rule to reference an
   existing one.

### For COVERAGE_GAP

1. **Empty selection:** add resources or tag conditions via
   `aws backup update-backup-selection --backup-plan-id <id>
   --backup-selection file://selection.json`. Use tag-based selection
   (`ListOfTags`) for dynamic environments; explicit ARNs for static
   critical resources.
2. **No selections:** create a selection with at least one resource or tag.

### For VAULT_RISK

1. **No lock:** enable compliance-mode lock immediately:
   `aws backup put-backup-vault-lock-configuration --backup-vault-name <vault> --min-retention-days 30 --changeable-for-days 0`
   (`--changeable-for-days 0` locks permanently — no cooling-off period).
2. **Governance-mode lock:** wait for `ChangeableForDays` to expire, or
   create a new vault with compliance-mode lock and migrate the plan.
3. **AWS-managed key:** create a CMK and update the vault:
   `aws backup update-backup-vault --backup-vault-name <vault> --encryption-key-arn <cmk-arn>`

### For NONCOMPLIANT

1. **Sub-daily frequency:** update the schedule to daily:
   `cron(0 5 * * ? *)` for 05:00 UTC daily.
2. **Insufficient retention:** increase `DeleteAfterDays` to >= 30. If the
   vault has a lock, ensure `DeleteAfterDays >= MinRetentionDays`.

### For OK

1. No remediation required for the current posture.
2. Recommend adding a report plan for automated compliance evidence:
   `aws backup create-report-plan`.
3. For production workloads, recommend a cross-region copy action if not
   already configured.

## Domain

AWS CloudOps / Backup, Recovery & Resilience Compliance.
