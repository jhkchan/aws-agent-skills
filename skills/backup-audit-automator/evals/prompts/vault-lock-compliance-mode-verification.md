# Eval: vault-lock-compliance-mode-verification

**Difficulty:** hard
**Branch:** AUTOMATION_DEPLOYED — compliance mode (immutable) verified, 365-day retention, KMS encryption check

## Prompt

Audit my backup vault named compliant-vault. I need to verify
it has Vault Lock in COMPLIANCE mode with 365-day retention.
The vault must be immutable. Also check that all recovery points
in this vault have KMS encryption. Account: 123456789012.
Region us-east-1.
