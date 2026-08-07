# Baseline (no-skill) response: aws-backup-restore-ready

This file captures what a generic assistant produces WITHOUT the
ec2-backup-operator skill loaded.

---

You can restore the recovery point with:

```bash
aws backup start-restore-job \
  --recovery-point-arn arn:aws:backup:us-east-1:111111111111:recovery-point:1a2b3c-4d5e-6f7g \
  --iam-role-arn arn:aws:iam::111111111111:role/service-role/AWSBackupRestoreRole \
  --metadata file://restore-metadata.json \
  --resource-type EC2
```

Wait for the restore job to complete with
`aws backup wait restore-job-completed --restore-job-id <id>`.
