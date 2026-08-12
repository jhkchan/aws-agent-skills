# Eval prompt: cross-region-verification

Design a cross-region backup replication verification workflow.
Emit the standard COMPLIANCE block (POLICY, LOCK, COVERAGE,
REPLICATION, VERDICT, TEMPLATE).

Design reference: cross-region-verification
Account: 111111111111
Source region: us-east-1
Destination region: us-west-2

Source vault: prod-backup-vault (us-east-1)
Destination vault: prod-backup-vault-dr (us-west-2)
Backup plan: includes copy rule to us-west-2.
Last 10 copy jobs: all COMPLETED.
KMS: source key us-east-1, destination key us-west-2 (separate).

Emit the standard COMPLIANCE block. Include the destination region
verification commands, the replication checklist, and the KMS key
validation for both regions.
