# Advanced Patterns — Backup Cross-Region Operator

## Mindset — the three cross-region realities
- **A backup vault is region-bound.** A vault exists in exactly one
  region. Cross-region copy creates a separate recovery point in
  the destination region's vault; it does NOT replicate the vault
  itself. The destination vault's name, KMS key, and lock
  configuration are independent of the source. Operators often
  assume the source vault's lock applies to the destination — it
  does not.

- **KMS key ownership matters for cross-account.** In same-account
  cross-region copy, the destination region KMS key is owned by
  the same account. In cross-account copy, the destination KMS key
  is owned by the destination account; the source account's
  `backup:StartCopyJob` role must be granted `kms:Decrypt` on the
  source KMS AND the destination account's KMS key policy must
  grant `kms:GenerateDataKey` and `kms:Decrypt` to
  `backup.<destination-region>.amazonaws.com` (and to the source
  account principal for cross-account re-encryption).

- **Cross-account copy requires AWS Organizations.** AWS Backup
  cross-account backup works ONLY when the source and destination
  accounts are in the same AWS Organization, and the Organizations
  backup policy (`backup-policy`) explicitly enables the
  cross-account relationship. Standalone cross-account copy via
  IAM alone is NOT supported — the operation returns
  `InvalidParameterValueException`.

## Step 0: Expert knowledge — non-obvious cross-region behaviors

- **Cross-region copy in a backup plan uses `CopyActions`.** The
  plan's `Rules[].CopyActions[]` array defines destination region,
  vault ARN, and lifecycle in destination. Each rule can have
  multiple `CopyActions` (multi-region DR).
- **`start-copy-job` is the manual alternative to a plan rule.**
  Use for one-off copies (DR drill, audit export). Returns a
  `CopyJobId`.
- **Cross-account copy requires Organizations.** Source and
  destination accounts must be in the same org, with an
  Organizations `BACKUP_POLICY` enabling the relationship. The
  destination vault's access policy must grant
  `backup:CopyIntoBackupVault` to the source account.
- **The destination vault access policy is the gate.** Without
  `backup:CopyIntoBackupVault` for the source account's role, the
  copy job fails with `AccessDeniedException`.
- **Cross-account KMS re-encryption is implicit.** Backup decrypts
  source with source key, re-encrypts with destination key. Both
  key policies must allow `backup.<region>.amazonaws.com` and (for
  cross-account) the source account principal.
- **Continuous backup (PITR) does NOT replicate point-in-time
  across regions.** Source region continuous backup is 1-second
  RPO within region. Cross-region copy is a point-in-time snapshot,
  NOT a continuous stream. Cross-region PITR requires
  application-level replication (Aurora Global, DynamoDB global
  tables).
- **Cross-region restore runs in the destination region.** Invoke
  `start-restore-job` in the destination region where the recovery
  point lives. IAM role and metadata are destination-region-specific.
- **Vault lock in source region does NOT prevent copy-out.**
  `MinRetentionDays` only blocks deletion; copy-out is allowed.
  Destination `MaxRetentionDays` caps the copy rule's
  `DeleteAfterDays`.
- **Copy duration depends on size and bandwidth.** EBS minutes;
  RDS 15-60 min; large EFS hours. Verify via `describe-copy-job`
  before launching restore.
- **Cross-account restore requires external key sharing.** When
  destination owns the recovery point and KMS key, the source
  account needs `kms:Decrypt` on the destination KMS key — via
  policy grant or `kms CreateGrant`.
- **Organizations backup policy is the source of truth for
  cross-account.** Tag-based selection in the org policy applies
  to ALL member accounts.
- **Backup Vault Lock cross-region is per-vault.** Locking the
  source vault does NOT lock the destination. Each region's vault
  must be locked separately.
- **Cross-region copy cost is per-GB-transferred + per-GB-stored.**
  For large frequent copies, consider async replication at the
  application layer (Aurora Global, S3 Cross-Region Replication).

## Expert heuristic: cross-region vs cross-account

```
CROSS-REGION (same account, different region)
   ├─ Use create-backup-plan with CopyActions[]
   ├─ Destination vault + KMS in destination region
   ├─ Same AWS account owns both regions
   └─ KMS re-encryption is implicit

CROSS-ACCOUNT (different accounts)
   ├─ Same AWS Organization required
   ├─ Organizations BACKUP_POLICY enables cross-account
   ├─ Destination vault access policy grants
   │   backup:CopyIntoBackupVault to source account
   ├─ Source role holds kms:Decrypt on source key
   ├─ Destination KMS policy grants kms:GenerateDataKey,
   │   kms:Decrypt to backup.<destination-region>.amazonaws.com
   │   AND to source account principal
   └─ IAM alone is NOT sufficient
```

**Per-resource-type cross-region caveats:**

| ResourceType | Cross-region behavior |
|---|---|
| `EC2` | Snapshot copied; restore creates new instance in destination |
| `RDS` | Snapshot copied; restore creates new DB instance |
| `EBS` | Snapshot copied; restore creates new volume |
| `S3` | Versioning backup copied; restore overwrites by version |
| `DynamoDB` | Backup copied; restore replaces table |
| `EFS` | File system copied; restore to new file system |
| `Aurora` | Cluster snapshot copied; restore to new cluster |
| `FSx` | Volume-level copy; filesystem-type-specific restore |

**Copy duration baselines:** EBS minutes; RDS 15-60 min; EFS hours;
FSx 30-120 min; S3 minutes-hours by object count.

ALWAYS pair cross-region copy with a quarterly DR drill — operators
often skip test-restore and discover permission gaps during an incident.

## Recent AWS features (2024-2026)

- **AWS Backup continuous backups cross-region (2025)**: continuous
  backup (PITR) for EC2 supports cross-region copy of the
  continuous recovery point; cross-region PITR still requires
  application-level replication.
- **Backup Vault Lock cross-region (2024)**: each region's vault
  lock is independent; the source region's lock does NOT apply to
  the destination region's vault. Locking the DR vault requires
  explicit `put-backup-vault-lock-configuration` in the
  destination region.
- **Cross-account backup via AWS Organizations (2023, refined
  2025)**: Organizations `BACKUP_POLICY` enables cross-account
  backup and restore; supports tag-based selection across member
  accounts; requires `backup:CopyIntoBackupVault` grant on the
  destination vault.
- **AWS Backup external key sharing (2024)**: cross-account
  restore with destination-owned KMS keys via KMS key policy or
  `kms CreateGrant`; supports air-gapped recovery patterns.
- **AWS Backup for Amazon FSx cross-region (2024)**: cross-region
  copy for FSx for Windows File Server, Lustre, OpenZFS, and
  NetApp ONTAP.
- **AWS Backup Audit Manager cross-region (2025)**: cross-region
  audit reporting and compliance frameworks.
