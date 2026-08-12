# Eval prompt: config-rule-compliance

Design a Config rules deployment for continuous backup compliance
monitoring across an AWS Organizations fleet. Emit the standard
COMPLIANCE block (POLICY, LOCK, COVERAGE, REPLICATION, VERDICT,
TEMPLATE).

Design reference: config-rule-compliance
Account: 111111111111 (management account)
Region: us-east-1

Organization: 30 member accounts.
Requirement: continuous backup compliance monitoring.
Managed rules needed: backup-recovery-point-encrypted,
  backup-recovery-point-manual-deletion-disabled.
Custom rule needed: EC2 must have backup plan tag.
Aggregation: management account Config aggregator.
Delegated admin: not yet configured.

Emit the standard COMPLIANCE block. Include the delegated
administrator setup, Config rule deployment commands, custom Lambda
rule summary, and the aggregation configuration.
