# Baseline (no-skill) response: config-rule-compliance

This file captures what a generic assistant produces WITHOUT the
backup-vault-compliance-automator skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, lock mode
selection, cool-off management, coverage audit, encryption
verification, cross-region replication, expert AWS Backup knowledge).

---

You can deploy Config rules to monitor backup compliance across your
organization. Set up the managed rules for encryption and vault
lock, then add a custom rule for EC2 backup tag coverage.

```
aws configservice put-config-rule \
  --config-rule '{"ConfigRuleName":"backup-encrypted","Source":{"Owner":"AWS","SourceIdentifier":"backup-recovery-point-encrypted"}}'
```

For the custom rule, write a Lambda function that checks if EC2
instances have the BackupPlan tag. Set up a Config aggregator in
the management account to see compliance across all accounts.
