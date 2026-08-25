# Backup Vault Operator — secondary worked examples

Content moved verbatim from SKILL.md (progressive disclosure). Load on demand.

---

### Worked example — create vault with KMS encryption (READY) (moved verbatim from SKILL.md)

```text
OPERATION: create-vault
VAULT: prod-daily-vault
VERDICT: READY
PRE_CHECKS:
  - [PASS] Vault name prod-daily-vault not already in use
  - [PASS] KMS key arn:aws:kms:us-east-1:111111111111:key/abcd1234
    KeyState Enabled, KeyManager CUSTOMER
  - [PASS] KMS key policy grants kms:GenerateDataKey, kms:Decrypt to
    backup.us-east-1.amazonaws.com
  - [PASS] Caller IAM role holds backup:CreateBackupVault
CHECKLIST:
  [✓]  Vault lock mode        current: UNLOCKED (new vault)                       recommended: apply COMPLIANCE lock separately (CIS 3.6) if regulatory
  [✗]  Backup plan rule       current: none (vault newly created)                 recommended: create plan with daily cron(0 5 ? * * *)
  [✗]  Lifecycle              current: none                                       recommended: MoveToColdStorageAfterDays 30, DeleteAfterDays 365 (adjust to mandate)
  [✗]  Cross-region copy      current: none                                       recommended: add CopyAction to dr-vault in us-west-2 if DR required
  [✓]  KMS encryption         current: arn:aws:kms:us-east-1:111111111111:key/abcd1234, KeyState Enabled   recommended: keep
  [✗]  Recovery points        current: 0 (new vault)                              recommended: confirm first recovery point COMPLETED within 24h of first plan run
  [✗]  Selection scope        current: none                                       recommended: tag-based selection backup=daily (auto-enrolls future resources)
STEPS:
  1. CONFIRM: About to create-backup-vault prod-daily-vault in account
     111111111111 region us-east-1. This will CREATE a new vault
     encrypted with KMS key abcd1234. The vault has no lock initially —
     apply lock-vault separately for WORM compliance. Proceed? (yes/no)
  2. aws backup create-backup-vault --backup-vault-name prod-daily-vault \
       --encryption-key-arn arn:aws:kms:us-east-1:111111111111:key/abcd1234-5678-90ef-1234-567890abcdef \
       --creator-request-id 1723305600 \
       --tags Environment=prod,Owner=platform-team
POST_VERIFY:
  - (pending execution)
  - aws backup describe-backup-vault --backup-vault-name prod-daily-vault returns EncryptionKeyArn set, NumberOfRecoveryPoints 0
STATE: pending — vault will be CREATED within ~30s
NOTES:
  - No vault lock applied. For compliance (CIS Benchmark 3.6), apply
    COMPLIANCE mode lock separately with MinRetentionDays >= 30.
  - KMS key is customer-managed — verify rotation is enabled via
    aws kms get-key-rotation-status --key-id abcd1234.
  - Tags Environment=prod, Owner=platform-team propagate to the vault
    for cost allocation and access control.
```

---

### Worked example — diagnose failed backup job (BLOCKED) (moved verbatim from SKILL.md)

```text
OPERATION: diagnose
VAULT: prod-daily-vault
VERDICT: BLOCKED
PRE_CHECKS:
  - [PASS] describe-backup-job returns the job (State FAILED,
    ResourceType EC2, BackupSizeInBytes 0)
  - [FAIL] IAM role AWSBackupDefaultServiceRole lacks ec2:CreateTags:
    CloudTrail shows AWSBackupServiceRole assumed at 2026-08-09T05:00:12Z
    attempting ec2:CreateTags on i-0123456789abcdef0 and receiving
    AccessDenied. The role policy includes ec2:CreateVolume,
    ec2:DescribeVolumes but not ec2:CreateTags. AWS Backup requires
    ec2:CreateTags on the snapshot.
  - [PASS] KMS key abcd1234 KeyState Enabled
CHECKLIST:
  [✓]  Vault lock mode        current: GOVERNANCE (soft lock)                     recommended: keep (operational policy, not regulatory)
  [✓]  Backup plan rule       current: DailyBackup, cron(0 5 ? * * *)              recommended: keep
  [✓]  Lifecycle              current: MoveToColdStorageAfterDays 30, DeleteAfterDays 365   recommended: keep
  [✗]  Cross-region copy      current: none                                       recommended: add CopyAction to dr-vault (single-region vault is a DR gap)
  [✓]  KMS encryption         current: arn:aws:kms:us-east-1:111111111111:key/abcd1234, KeyState Enabled   recommended: keep
  [✗]  Recovery points        current: 14 points, latest FAILED (job abc123)      recommended: remediate IAM, re-run with idempotency token
  [✓]  Selection scope        current: tag-based backup=daily, env=prod           recommended: keep
STEPS: (none — pre-checks failed; this is a diagnosis)
POST_VERIFY: (none)
STATE: FAILED — IAM role missing ec2:CreateTags permission
NOTES:
  - Remediation: add ec2:CreateTags, ec2:DeleteTags, ec2:DescribeTags to
    the AWSBackupDefaultServiceRole policy.
  - Re-run the backup with idempotency:
    aws backup start-backup-job --backup-vault-name prod-daily-vault \
      --resource-arn arn:aws:ec2:us-east-1:111111111111:instance/i-0123456789abcdef0 \
      --iam-role-arn arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole \
      --idempotency-token "$(date +%s)"
```

