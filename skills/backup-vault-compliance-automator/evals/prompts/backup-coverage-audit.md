# Eval prompt: backup-coverage-audit

Design a backup plan coverage audit for an account with resources
lacking backup plans. Emit the standard COMPLIANCE block (POLICY,
LOCK, COVERAGE, REPLICATION, VERDICT, TEMPLATE).

Design reference: backup-coverage-audit
Account: 111111111111
Region: us-east-1

Total resources: 85 (EC2=40, RDS=15, DynamoDB=20, EFS=10)
Backup selections: tag-based (BackupPlan=prod) covering 82.
Gap: 3 EC2 instances lack the BackupPlan tag.
Existing Config rules: none for backup coverage.
Requirement: all production resources must have daily backups.

Emit the standard COMPLIANCE block. Address the coverage gap, the
Config rule recommendation for continuous detection, and the
tagging remediation steps.
