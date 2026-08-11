# Cross-account backup and Organizations policy guide

This reference covers the cross-account backup model — when to use
it, the Organizations policy structure, and the IAM / vault access
policy gates that make cross-account copy work.

## Cross-account requirements

AWS Backup cross-account backup requires ALL of:

1. Source and destination accounts in the **same AWS Organization**.
2. The Organizations `BACKUP_POLICY` type enabled.
3. A `BACKUP_POLICY` attached to the source account, destination
   account, or root, defining the cross-account relationship.
4. The destination vault's **access policy** grants
   `backup:CopyIntoBackupVault` to the source account.
5. Source backup role holds `backup:StartCopyJob` and
   `backup:CopyIntoBackupVault`.
6. Source KMS key policy grants `kms:Decrypt` to the source backup
   role.
7. Destination KMS key policy grants `kms:GenerateDataKey` and
   `kms:Decrypt` to `backup.<destination-region>.amazonaws.com`
   AND to the source account principal.

Without ALL of these, the cross-account copy fails.

## Organizations backup policy structure

```json
{
  "plans": [
    {
      "rules": [
        {
          "rule-name": "DailyToCentral",
          "target-backup-vault-name": "source-vault",
          "schedule-expression": "cron(0 5 ? * * *)",
          "start-window-minutes": 480,
          "completion-window-minutes": 1440,
          "copy-actions": [
            {
              "destination-backup-vault-arn": "arn:aws:backup:us-east-1:CENTRAL_ACCOUNT:backup-vault:central-vault",
              "lifecycle": {"delete-after-days": 90}
            }
          ]
        }
      ],
      "selection-list": [
        {
          "selection-name": "tag-based",
          "iam-role-arn": "arn:aws:iam::SOURCE_ACCOUNT:role/service-role/AWSBackupDefaultServiceRole",
          "list-of-tags": [
            {
              "condition-type": "STRINGEQUALS",
              "condition-key": "backup",
              "condition-value": "central"
            }
          ]
        }
      ]
    }
  ]
}
```

The policy is attached to an Organizations root, OU, or account.
The `destination-backup-vault-arn` references the CENTRAL (target)
account's vault.

## Destination vault access policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::SOURCE_ACCOUNT:root"
      },
      "Action": "backup:CopyIntoBackupVault",
      "Resource": "*"
    }
  ]
}
```

Apply via `aws backup put-backup-vault-access-policy --backup-vault-name
central-vault --policy file://policy.json --region us-east-1`.

## Cross-account KMS sharing

Source KMS key policy must grant `kms:Decrypt` to the source backup
role:

```json
{
  "Effect": "Allow",
  "Principal": {"AWS": "arn:aws:iam::SOURCE_ACCOUNT:role/service-role/AWSBackupDefaultServiceRole"},
  "Action": ["kms:Decrypt", "kms:DescribeKey"],
  "Resource": "*"
}
```

Destination KMS key policy must grant to BOTH the
`backup.<destination-region>.amazonaws.com` service principal AND
the source account:

```json
{
  "Effect": "Allow",
  "Principal": {
    "Service": "backup.<destination-region>.amazonaws.com",
    "AWS": "arn:aws:iam::SOURCE_ACCOUNT:root"
  },
  "Action": ["kms:GenerateDataKey", "kms:Decrypt", "kms:DescribeKey"],
  "Resource": "*"
}
```

## Common cross-account failures

| Symptom | Root cause | Fix |
|---|---|---|
| `AccessDeniedException` on `StartCopyJob` | Source role lacks `backup:StartCopyJob` | Add to source role policy |
| `AccessDeniedException` writing to destination vault | Destination vault policy missing source principal | Add `backup:CopyIntoBackupVault` grant |
| `KMSAccessDeniedException` | KMS policy missing source account or service principal | Update KMS key policies on both sides |
| `InvalidParameterValueException` | Source and destination not in same org | Invite destination to org, or fall back to same-account |
| Copy job stuck `RUNNING > 6h` | Large snapshot OR KMS propagation delay | Wait or contact support |

## Cross-account restore

For restoring cross-account backups back to the source:

1. Source account assumes a role with `backup:StartRestoreJob` in
   the destination account (or vice versa).
2. Destination KMS key must grant `kms:Decrypt` to the role
   performing the restore.
3. The restore runs in the region where the recovery point lives
   (destination region).
4. The restored resource is created in the destination account.

For external-key-sharing restore patterns (air-gapped recovery),
use `kms CreateGrant` to delegate temporary decrypt access to the
restore role.
