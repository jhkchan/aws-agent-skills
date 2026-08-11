# Vault Lock and Compliance — Backup Vault Deployer

Deep reference on vault lock modes (governance vs compliance),
retention window enforcement, ChangeableForDays grace period
mechanics, compliance framework mapping (CIS, NIST, SEC 17a-4),
and lifecycle-within-lock-window validation. Loaded on demand by
the skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## Vault lock modes in detail

### Governance mode

```text
Properties:
  ├── Lock can be REMOVED by privileged users
  │     Requires: backup:DeleteBackupVault + backup:PutBackupVaultLockConfiguration
  ├── Min/Max retention enforced for non-privileged users
  ├── No grace period — can be added/removed freely
  └── Provides soft protection against accidental deletion

Use cases:
  ├── Prevent accidental deletion by most operators
  ├── Development and test environments
  └── Environments where privileged break-glass is acceptable

NOT suitable for:
  ├── Regulatory compliance (CIS, NIST, SEC 17a-4)
  ├── Anti-ransomware immutability requirements
  └── Any scenario where the lock must be irrevocable
```

### Compliance mode

```text
Properties:
  ├── Lock is IRREVOCABLE after ChangeableForDays grace period
  ├── NO user can remove the lock (including root)
  ├── Min/Max retention enforced for ALL users (including root)
  ├── Grace period: ChangeableForDays (default 3, max 30)
  │     During grace: lock configuration CAN be modified
  │     After grace: lock configuration is PERMANENT
  └── Provides regulatory-grade WORM immutability

Use cases:
  ├── SEC Rule 17a-4 (broker-dealer records)
  ├── CFTC (commodity futures)
  ├── FINRA (financial industry)
  ├── HIPAA audit trails
  ├── CIS Benchmark 3.6 (backup vault lock)
  └── Anti-ransomware defense-in-depth
```

### Mode selection decision tree

```text
Regulatory requirement?
  ├── YES → COMPLIANCE MODE (no exceptions)
  │     CIS 3.6? → COMPLIANCE
  │     SEC 17a-4? → COMPLIANCE
  │     NIST CP-9? → COMPLIANCE
  │     HIPAA? → COMPLIANCE
  │
  └── NO → Assess risk tolerance
        ├── Need irrevocable protection? → COMPLIANCE
        ├── Accept privileged-user break-glass? → GOVERNANCE
        └── No lock needed? → NONE (not recommended for production)
```

## Retention window enforcement

### How the lock enforces retention

Vault lock enforces retention for ALL backup plan rules targeting
the vault:

```text
Vault lock: MinRetentionDays=90, MaxRetentionDays=365

ALL backup rules targeting this vault must have:
  DeleteAfterDays >= MinRetentionDays (90)
  DeleteAfterDays <= MaxRetentionDays (365)
  MoveToColdStorageAfterDays < DeleteAfterDays

If a rule violates this → backup job FAILS
```

### Lifecycle validation matrix

```text
Scenario              | DeleteAfter | MinRetention | MaxRetention | Result
----------------------|-------------|--------------|--------------|--------
Too short             | 7           | 90           | 365          | FAIL
At minimum            | 90          | 90           | 365          | PASS
Within window         | 180         | 90           | 365          | PASS
At maximum            | 365         | 90           | 365          | PASS
Too long              | 730         | 90           | 365          | FAIL
No max set            | 730         | 90           | (none)       | PASS
```

### Cold storage interaction

```text
MoveToColdStorageAfterDays must be LESS THAN DeleteAfterDays:

  MoveToCold=60, Delete=180 → PASS (objects cold after 60d, deleted at 180d)
  MoveToCold=180, Delete=180 → INVALID (cannot move and delete on same day)
  MoveToCold=200, Delete=180 → FAIL (cannot move to cold AFTER deletion)
```

## ChangeableForDays grace period

### Mechanics

```text
Day 0: put-backup-vault-lock-configuration --mode COMPLIANCE
       --changeable-for-days 3

Day 0-3: Lock configuration CAN be modified
  ├── Can change MinRetentionDays, MaxRetentionDays
  ├── Can remove the lock entirely
  └── This is the ONLY window for corrections

Day 4+: Lock is IRREVOCABLE
  ├── Cannot change MinRetentionDays, MaxRetentionDays
  ├── Cannot remove the lock
  ├── No user (including root) can modify or remove
  └── Recovery points CANNOT be deleted before MinRetentionDays
```

### Best practices for ChangeableForDays

```text
Recommended: 3 days (default)
  ├── Gives time to verify lock configuration
  ├── Allows correction if Min/Max retention is wrong
  └── Short enough to prevent indefinite uncertainty

Maximum: 30 days
  ├── Use only if compliance team review takes >3 days
  └── During this window, the lock is effectively governance-mode

Common mistake: ChangeableForDays=0
  ├── Lock becomes irrevocable IMMEDIATELY
  ├── If retention is wrong, cannot be fixed
  └── Always use at least 3 days
```

## Compliance framework mapping

| Framework | Requirement | Vault lock mode | Min retention |
|---|---|---|---|
| CIS AWS Benchmark 3.6 | Ensure backup vault lock is enabled | Compliance or Governance | Per policy |
| NIST SP 800-34 (CP-9) | System backup | Compliance | Per RPO/RTO |
| SEC Rule 17a-4 | Broker-dealer records retention | Compliance (WORM) | 36-72 months |
| CFTC 1.31 | Records retention | Compliance (WORM) | 5 years |
| FINRA 4511 | Books and records | Compliance (WORM) | 6 years |
| HIPAA 164.310(d)(2)(iv) | Data backup | Compliance | Per policy |
| PCI-DSS 12.10 | Incident response data | Compliance | 1 year |
| SOX 7(a) | Financial records | Compliance | 7 years |

## Vault lock CLI commands

```bash
# Apply compliance-mode lock with 3-day grace period
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name production-backup-vault \
  --region us-east-1 \
  --min-retention-days 90 \
  --max-retention-days 365 \
  --changeable-for-days 3 \
  --mode COMPLIANCE

# Apply governance-mode lock
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name dev-backup-vault \
  --region us-east-1 \
  --min-retention-days 7 \
  --max-retention-days 90 \
  --mode GOVERNANCE

# Verify lock state
aws backup describe-backup-vault \
  --backup-vault-name production-backup-vault \
  --region us-east-1 \
  --query '{Locked:LockedDate,MinRetention:MinRetentionDays,MaxRetention:MaxRetentionDays}'

# Remove governance-mode lock (privileged users only)
aws backup delete-backup-vault-lock-configuration \
  --backup-vault-name dev-backup-vault \
  --region us-east-1
# NOTE: This only works for GOVERNANCE mode. COMPLIANCE mode is irrevocable.
```

## Terraform examples

```hcl
# Compliance-mode vault lock
resource "aws_backup_vault_lock_configuration" "compliance" {
  backup_vault_name   = aws_backup_vault.production.name
  changeable_for_days = 3
  min_retention_days  = 90
  max_retention_days  = 365
  mode                = "COMPLIANCE"
}

# Governance-mode vault lock
resource "aws_backup_vault_lock_configuration" "governance" {
  backup_vault_name   = aws_backup_vault.development.name
  min_retention_days  = 7
  max_retention_days  = 90
  mode                = "GOVERNANCE"
}

# Backup plan with lifecycle within lock window
resource "aws_backup_plan" "production" {
  name = "production-daily-backup"

  rule {
    rule_name         = "daily-backup"
    target_vault_name = aws_backup_vault.production.name
    schedule          = "cron(0 5 ? * MON-SAT *)"

    lifecycle {
      cold_storage_after = 60
      delete_after       = 180  # Must be >= min_retention_days (90) and <= max (365)
    }
  }
}
```
