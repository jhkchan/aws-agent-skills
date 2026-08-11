# Baseline (no-skill) response: start-cross-region-copy-ready

This file captures what a generic assistant produces WITHOUT the
backup-cross-region-operator skill loaded.

---

To start a cross-region copy job:

```bash
aws backup start-copy-job \
  --recovery-point-arn arn:aws:backup:us-east-1:111111111111:recovery-point:1-2-3-4 \
  --source-backup-vault-name prod-daily-vault \
  --destination-backup-vault-arn arn:aws:backup:us-west-2:111111111111:backup-vault:dr-vault \
  --iam-role-arn arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole \
  --region us-east-1
```

You can check the status with `describe-copy-job`.
