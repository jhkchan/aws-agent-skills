# Worked Examples — Backup Cross-Region Operator

## Worked example — start cross-region copy (READY)

```text
OPERATION: start-copy
VERDICT: READY
TARGET: recovery-point 1-2-3-4 (us-east-1) -> dr-vault (us-west-2)
PRE_CHECKS:
  - [PASS] Source recovery point 1-2-3-4 Status COMPLETED
  - [PASS] Destination vault dr-vault exists in us-west-2
  - [PASS] Source IAM role AWSBackupDefaultServiceRole holds
    backup:StartCopyJob
  - [PASS] Source KMS key grants kms:Decrypt to backup.us-east-1
  - [PASS] Destination KMS key grants kms:GenerateDataKey to
    backup.us-west-2
STEPS:
  1. CONFIRM: About to start-copy-job for recovery point 1-2-3-4
     from prod-daily-vault (us-east-1) to dr-vault (us-west-2).
     Duration: minutes to hours depending on size. Proceed? (yes/no)
  2. aws backup start-copy-job --recovery-point-arn arn:aws:backup:us-east-1:111111111111:recovery-point:1-2-3-4 \
       --source-backup-vault-name prod-daily-vault \
       --destination-backup-vault-arn arn:aws:backup:us-west-2:111111111111:backup-vault:dr-vault \
       --iam-role-arn arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole \
       --idempotency-token 1723305600 --region us-east-1
POST_VERIFY:
  - (pending execution)
  - describe-copy-job returns State COMPLETED and
    DestinationRecoveryPointArn within minutes to hours
  - list-recovery-points-by-backup-vault --backup-vault-name dr-vault
    --region us-west-2 shows the new recovery point
STATE: pending — copy job COMPLETED within minutes to hours
NOTES:
  - Same-account cross-region copy. KMS re-encryption is implicit.
  - Destination recovery point uses destination KMS key (xyz).
  - Cost: per-GB-transferred + per-GB-stored in us-west-2.
```

## Worked example — cross-account copy BLOCKED

```text
OPERATION: cross-account-enable
VERDICT: BLOCKED
TARGET: account 111111111111 -> account 222222222222 (cross-account)
PRE_CHECKS:
  - [FAIL] Source 111111111111 is NOT in the same AWS Organization
    as destination 222222222222. describe-organization returns
    ManagementAccountId 999999999999; 222222222222 is NOT a member.
  - [PASS] Caller holds organizations:DescribeEffectivePolicy
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
STATE: FAILED — cross-account requires same AWS Organization
NOTES:
  - Remediation: invite 222222222222 to the org, then attach a
    BACKUP_POLICY enabling cross-account. Standalone cross-account
    copy is NOT supported.
  - Alternative: copy to a same-account destination region.
```
