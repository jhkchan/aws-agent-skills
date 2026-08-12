# Baseline (no-skill) response: backup-coverage-audit

This file captures what a generic assistant produces WITHOUT the
backup-vault-compliance-automator skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, lock mode
selection, cool-off management, coverage audit, encryption
verification, cross-region replication, expert AWS Backup knowledge).

---

You have 3 EC2 instances without the backup tag. Just add the
BackupPlan=prod tag to them and they'll be picked up by your
backup selection.

```
aws ec2 create-tags --resources i-xxx --tags Key=BackupPlan,Value=prod
```

You could also set up a Config rule to check for resources without
backup tags. That way you'll be alerted when new instances are
created without the tag.
