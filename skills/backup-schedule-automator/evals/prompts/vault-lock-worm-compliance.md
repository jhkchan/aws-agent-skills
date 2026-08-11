# Eval prompt: vault-lock-worm-compliance

Design a compliance backup workflow with WORM vault lock for the
following workload. Emit the standard BACKUP block including the vault
lock configuration (GOVERNANCE first, then COMPLIANCE).

Design reference: vault-lock-worm-compliance
Account: 111111111111
Region: us-east-1

Compliance requirement: SOX (7-year retention, WORM)
Resources: RDS instances tagged backup-plan=compliance, environment=prod
Backup frequency: Daily
Retention: 365 days hot, 2555 days (7 years) cold
Vault lock: required (COMPLIANCE mode, min 365d, max 2555d)
IAM role: arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole

Include the GOVERNANCE-mode test step before switching to COMPLIANCE.
