# Eval prompt: empty-tag-scope-gap

Audit the existing AWS Backup configuration and identify all gaps.
Emit the standard BACKUP block identifying every missing piece.

Design reference: empty-tag-scope-gap
Account: 111111111111
Region: us-east-1

Existing plan: daily-7d (Default vault, no lock)
Tag scope: backup-plan=daily (0 resources currently match)
Lifecycle: NONE (all backups in hot storage indefinitely)
Restore testing: NOT configured
Vault: Default (no access policy, no lock, no notifications)
Cross-region: NONE
Cross-account: NONE

The audit should identify all gaps and provide the REVIEW_REQUIRED
verdict with specific remediation steps.
