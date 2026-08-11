# Vault Lock and Compliance Reference

Load this reference when planning or executing any vault lock operation.
The procedures below are the canonical sequences for compliance mode vs
governance mode, with pre-checks, command sequence, post-verification,
and rollback caveats.

## Decision tree — which lock mode

| Scenario | Use | Why |
|---|---|---|
| Regulatory requirement (CIS 3.6, NIST CP-9, FedRAMP, HIPAA, SOX) | **COMPLIANCE mode** | Lock cannot be removed even by root after grace; satisfies auditor immutability requirement |
| Internal operational policy (no regulator) | **GOVERNANCE mode** | Soft lock — removable by privileged principal; sufficient for guardrails |
| Need to reverse lock decision | **GOVERNANCE mode** or **COMPLIANCE with ChangeableForDays** | Compliance with grace window <= 3 days allows reversal; after grace, irreversible |
| Multi-year regulatory archive | **COMPLIANCE mode**, MaxRetentionDays = regulatory ceiling | Lock enforces retention floor and ceiling |
| Testing vault lock behavior | **GOVERNANCE mode** | Can be removed without waiting for grace |

## Compliance mode procedure (WORM, immutable)

**When to use:** regulatory archives, audit-bound retention, root-proof
immutability.

**Pre-checks:**
1. `describe-backup-vault --backup-vault-name <vault>` returns the
   vault with `VaultLock.LockState` absent or `UNLOCKED`.
2. KMS key (referenced by `EncryptionKeyArn`) is `Enabled`.
3. `MinRetentionDays` >= longest existing recovery point age in the
   vault (else existing points cannot be deleted on existing
   schedule).
4. `MaxRetentionDays` >= longest plan lifecycle retention writing to
   the vault (else plans will fail to delete within the ceiling).
5. `ChangeableForDays` <= 3 (AWS maximum grace window).
6. Caller IAM role holds
   `backup:PutBackupVaultLockConfiguration`.

**Command sequence:**
```bash
# 1. Snapshot existing vault metadata (no rollback path for lock
#    after grace, so capture state for audit)
aws backup describe-backup-vault \
  --backup-vault-name prod-compliance-vault \
  --output json > /tmp/prod-compliance-vault-pre-lock-$(date +%s).json

# 2. CONFIRM gate, then put-backup-vault-lock-configuration
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name prod-compliance-vault \
  --changeable-for-days 3 \
  --min-retention-days 30 \
  --max-retention-days 3650
```

**Post-verification:**
```bash
aws backup describe-backup-vault \
  --backup-vault-name prod-compliance-vault \
  --query 'VaultLock'
# Expected: LockState=LOCKED, Mode=COMPLIANCE, MinRetentionDays=30,
#           MaxRetentionDays=3650, ChangeableForDays=3
```

## Governance mode procedure (soft, mutable by privileged)

**When to use:** operational guardrails without regulatory mandate.

**Command sequence:**
```bash
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name prod-governance-vault \
  --mode GOVERNANCE \
  --min-retention-days 30 \
  --max-retention-days 365
```

**Removal (privileged principal):**
```bash
aws backup delete-backup-vault-lock-configuration \
  --backup-vault-name prod-governance-vault
```

Requires `backup:DeleteBackupVaultLockConfiguration` on the caller.

## Retention window semantics

The vault lock has TWO retention fields:

- **`MinRetentionDays`**: floor. Recovery points cannot be deleted
  before this age. Backup plan lifecycles that specify
  `DeleteAfterDays < MinRetentionDays` are silently clamped — the
  recovery point is retained past the plan's deletion target.
- **`MaxRetentionDays`**: ceiling. Recovery points cannot be retained
  past this age. The lock enforces mandatory deletion; useful for
  GDPR/CCPA right-to-be-forgotten compliance.

Backup plan lifecycle `MoveToColdStorageAfterDays` and
`DeleteAfterDays` must fit within the lock window:
```
MinRetentionDays <= MoveToColdStorageAfterDays <= DeleteAfterDays <= MaxRetentionDays
```

Out-of-window values produce plan execution errors at the lifecycle
transition time, not at plan creation.

## Compliance mapping

| Standard | Required posture | MinRetentionDays | Recommended mode |
|---|---|---|---|
| CIS AWS Benchmark 3.6 | "Ensure AWS Backup vaults are locked" | Service-specific; usually >= 30 | COMPLIANCE |
| NIST 800-53 CP-9 | "Long-term backup retention" | >= 90 for federal | COMPLIANCE |
| HIPAA Security Rule | "Exact backup and restore" | 6 years (2189 days) for HIPAA-related data | COMPLIANCE |
| SOX | "Records retention for audit" | 7 years (2555 days) for financial records | COMPLIANCE |
| PCI DSS | "Backup for disaster recovery" | 1 year (365 days) for PCI data | COMPLIANCE |
| GDPR / CCPA | "Right to erasure" | n/a; MaxRetentionDays enforces ceiling | COMPLIANCE with MaxRetentionDays |

## Common lock misconfigurations

1. **Setting MinRetentionDays below existing recovery point age:**
   the lock applies to existing points. If a point is 60 days old and
   MinRetentionDays is 30, the point can be deleted normally — but if
   MinRetentionDays is 90, the point must be retained an additional 30
   days.

2. **Forgetting ChangeableForDays:** without it, the lock is
   immediately permanent. Always set `ChangeableForDays 3` for a
   reversal window during the initial rollout.

3. **Locking a vault with a default-AWS-managed KMS key:** the lock
   applies to the vault, not the key. If the KMS key is later rotated
   (with a new ARN), existing recovery points remain encrypted with
   the original key. The vault lock does not prevent key rotation, but
   recovery points become unrecoverable if the original key is
   deleted.

4. **Mixing compliance and governance:** a vault can only have ONE
   lock configuration. Applying a new lock replaces the existing
   configuration. Compliance mode cannot be "downgraded" to
   governance after the grace window.
