# Eval prompt: vault-lock-compliance-mode

Design a Vault Lock deployment in compliance mode for regulatory
retention requirements. Emit the standard COMPLIANCE block (POLICY,
LOCK, COVERAGE, REPLICATION, VERDICT, TEMPLATE).

Design reference: vault-lock-compliance-mode
Account: 111111111111
Region: us-east-1

Vault: compliance-vault
Requirement: SEC 17a-4 immutable retention, 7 years (2557 days).
Current state: vault exists, no lock, 50 recovery points all encrypted.
Vault policy: deny-non-encrypted (already deployed).
KMS key: arn:aws:kms:us-east-1:111111111111:key/compliance-key
Pre-deployment validation: tested governance mode in staging.

Emit the standard COMPLIANCE block. Include the lock configuration
CLI, the cool-off period management steps, and the post-lock
verification commands.
