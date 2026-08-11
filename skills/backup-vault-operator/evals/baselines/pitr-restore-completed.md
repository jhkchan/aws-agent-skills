# Baseline (no-skill) response: pitr-restore-completed

This file captures what a generic assistant produces WITHOUT the
backup-vault-operator skill loaded.

---

To restore an EC2 instance from a recovery point, use:

```bash
aws backup start-restore-job \
  --recovery-point-arn arn:aws:backup:us-east-1:111111111111:recovery-point:1-2-3-4 \
  --metadata '{"InstanceId":"i-restored-pitr"}' \
  --iam-role-arn arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole \
  --resource-type EC2
```

Verify the restore is complete via
`aws backup describe-restore-job --restore-job-id <id>`.
