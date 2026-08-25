# Backup Schedule Automator — expert-heuristic deep dives, Step-0 expert knowledge, pitfall catalog, recent AWS features

Content moved verbatim from SKILL.md (progressive disclosure). Load on demand.

---

## Expert heuristic — tag-based scaling, vault lock WORM, restore testing vs RTO (moved verbatim from SKILL.md)

**Tag-based resource assignment scaling + vault lock for compliance (WORM) +
restore testing frequency vs RTO/RPO validation.**

The highest-leverage Backup automation pattern combines three design
decisions:

1. **Tag-based assignment at scale:** Resources are tagged
   `backup-plan=<plan-name>` and `backup-env=<env>`. The backup plan's
   `Selection` uses `Conditions: StringEquals` on these tags. When a new
   resource is created with the tag, it is automatically included in the
   next backup window. A CloudWatch alarm on `NumberOfResourcesAssigned`
   dropping to zero catches tag drift.

2. **Vault lock for WORM compliance:** For regulated workloads (financial,
   healthcare, legal), the backup vault is locked in COMPLIANCE mode with
   a retention period matching the regulatory requirement (e.g., 7 years
   for SOX, 6 years for HIPAA). This prevents even the root account from
   deleting backups before the retention period expires.

3. **Restore testing frequency mapped to RTO:**

| Application tier | RTO target | Restore test frequency | Acceptable |
|---|---|---|---|
| Tier 1 (production critical) | < 1 hour | Weekly | Restore + app health check |
| Tier 2 (production standard) | < 4 hours | Monthly | Restore + data integrity check |
| Tier 3 (internal/dev) | < 24 hours | Quarterly | Restore only |

**Tag-based scaling pattern:**

```yaml
# Backup selection using tag-based conditions
BackupSelection:
  SelectionName: "daily-prod-selection"
  IamRoleArn: "arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole"
  ListOfTags:
    - ConditionType: "STRINGEQUALS"
      ConditionKey: "backup-plan"
      ConditionValue: "daily-prod"
  Conditions:
    StringEquals:
      - ConditionKey: "aws:ResourceTag/environment"
        ConditionValue: "prod"
  NotResources:
    - "arn:aws:dynamodb:us-east-1:111111111111:table/temp-*"
```

**Vault lock compliance pattern:**

```bash
# Step 1: Create vault
aws backup create-backup-vault \
  --backup-vault-name "prod-compliance-vault" \
  --encryption-key-arn "arn:aws:kms:us-east-1:111111111111:key/abc123"

# Step 2: Lock in GOVERNANCE mode first (test)
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name "prod-compliance-vault" \
  --changeable-for-days 3 \
  --min-retention-days 30 \
  --max-retention-days 2555 \
  --mode GOVERNANCE

# Step 3: After validation, switch to COMPLIANCE (irreversible)
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name "prod-compliance-vault" \
  --min-retention-days 365 \
  --max-retention-days 2555 \
  --mode COMPLIANCE
```

---

### Step 0: Expert knowledge — non-obvious Backup behaviors (moved verbatim from SKILL.md)

- **Backup plan rules are evaluated independently.** If a plan has two
  rules (daily-7d and weekly-30d), a resource matching both rules gets
  TWO backups on the weekly schedule day. Use `CopyActions` within a
  single rule to avoid duplicate backups.

- **Tag-based selection is evaluated at backup time, not at plan creation.**
  Resources tagged after the plan is created are automatically included
  in the next backup window. Resources with the tag removed are
  excluded. No plan update is needed.

- **The default backup vault (`Default`) has NO access policy.** Any
  principal with `backup:StartBackupJob` can write to it. Always create
  named vaults with explicit access policies for production workloads.

- **Cross-account backup uses the DESTINATION vault's KMS key.** The
  source account cannot use its own KMS key for a backup written to a
  destination account's vault. The destination KMS key policy must grant
  the source account `kms:Decrypt` and `kms:GenerateDataKey`.

- **Lifecycle `DeleteAfterDays` is measured from the backup creation
  date.** A recovery point created on Jan 1 with `DeleteAfterDays=30`
  is eligible for deletion on Jan 31. `MoveToColdStorageAfterDays` works
  the same way.

- **`start-restore-job` is asynchronous.** The API returns a `RestoreJobId`
  immediately. The actual restore takes minutes to hours depending on
  data size and storage tier. Poll `describe-restore-job` for completion.

- **Organizations backup policies override account-level plans.** If a
  policy at the OU level specifies a backup plan, member accounts cannot
  create conflicting plans. The policy merges with any account-level
  plans, and the more restrictive retention wins.

- **Backup reports are delivered to S3 with a delay.** A daily report
  plan delivers the previous day's data. Real-time job status requires
  CloudWatch Events (`Backup Job State Change`).

- **Vault lock `ChangeableForDays` only applies to GOVERNANCE mode.**
  During this window, an admin can modify or remove the lock. After the
  window expires, the lock becomes immutable (functionally identical to
  COMPLIANCE mode).

---

## Recent AWS features (2024-2026) (moved verbatim from SKILL.md)

- **Backup vault lock GA (2024):** WORM compliance for backup vaults.
  GOVERNANCE mode for testing; COMPLIANCE mode for production.
- **Restore testing automation (2024-2025):** Scheduled Lambda-driven
  restore testing with CloudWatch metrics for RTO/RPO tracking.
- **Organizations backup policies (2024):** Centralized backup plan
  management across all member accounts with policy inheritance.
- **Backup frameworks (2025):** Compliance controls for backup frequency,
  retention, and encryption, with automated reporting.
- **Cross-account backup via KMS grants (2025-2026):** Simplified KMS key
  sharing for cross-account backup without manual key policy management.

---

## Expert heuristic: blast radius of vault lock (moved verbatim from SKILL.md)

> ALWAYS test vault lock in GOVERNANCE mode for at least 3 days before
> switching to COMPLIANCE mode. A COMPLIANCE lock with a mistyped
> retention period is an irreversible commitment that can cost thousands
> in unnecessary storage.

**Pre-production validation protocol:**

1. Create vault. Enable GOVERNANCE lock with `ChangeableForDays=3`.
2. Run backup + restore cycle. Verify both succeed.
3. Test lock enforcement: attempt early deletion (should fail).
4. After 3 days, if all checks pass, switch to COMPLIANCE mode.
5. Verify with `describe-backup-vault` that mode is COMPLIANCE and
   retention values are correct.

---

## Anti-Patterns — NEVER do these things (moved verbatim from SKILL.md)

- NEVER deploy a backup plan without verifying that tagged resources
  exist. The backup service does not warn on empty selection. A plan
  matching zero resources silently backs up nothing.

- NEVER enable vault lock in COMPLIANCE mode without GOVERNANCE testing.
  COMPLIANCE mode is irreversible. A retention typo commits you to
  decades of storage costs.

- NEVER configure cold storage transition without documenting thaw time.
  Cold storage restores take hours. If the RTO is 1 hour, cold storage
  at day 31 breaks the SLA.

- NEVER assume cross-account backup works without the destination KMS
  key policy. The source account needs `kms:Decrypt` and
  `kms:GenerateDataKey` on the destination key.

- NEVER skip restore testing. An untested backup is a liability. Schedule
  restore tests at a frequency mapped to the application RTO.

- NEVER use the Default backup vault for production. Create named vaults
  with explicit access policies and notifications.

- NEVER configure on-demand backup without a DLQ. EventBridge delivers
  asynchronously; failed triggers are silently dropped.

- NEVER rely solely on backup reports for compliance. Pair reports with
  restore-test logs for audit completeness.

