# Eval prompt: vault-policy-enforcement

Design a backup vault policy that enforces encryption and approved
KMS key usage with cross-account access. Emit the standard COMPLIANCE
block (POLICY, LOCK, COVERAGE, REPLICATION, VERDICT, TEMPLATE).

Design reference: vault-policy-enforcement
Account: 111111111111
Region: us-east-1

Vault: prod-backup-vault
Requirement: deny all non-encrypted backups, enforce approved KMS key.
Current policy: default (open access).
Approved KMS key: arn:aws:kms:us-east-1:111111111111:key/prod-backup-key
Cross-account: source account 222222222222 needs write access.

Emit the standard COMPLIANCE block. Include the full vault policy
JSON with deny-non-encrypted, KMS enforcement, TLS requirement, and
cross-account allow statements.
