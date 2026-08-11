# Eval prompt: governance-mode-misuse-blocked

User requests governance mode for a HIPAA-regulated archive vault.
Plan the operation and emit the standard VERDICT block.

Operation: lock-vault
Vault name: hipaa-archive-vault
Region: us-east-1
Requested mode: GOVERNANCE
MinRetentionDays: 2189
MaxRetentionDays: 2555
Compliance driver: HIPAA Security Rule

```json
{
  "VaultState": {
    "describe-backup-vault.hipaa-archive-vault": {
      "VaultLock": {"LockState": null},
      "exists": true,
      "tagged_resources": ["PHI"]
    },
    "caller_iam": {
      "role": "AWSBackupOperatorRole",
      "permissions": ["backup:PutBackupVaultLockConfiguration"]
    },
    "compliance_scan": {
      "regulation": "HIPAA",
      "requires_immutable": true,
      "governance_mode_meets_immutable": false,
      "compliance_mode_meets_immutable": true
    }
  }
}
```
