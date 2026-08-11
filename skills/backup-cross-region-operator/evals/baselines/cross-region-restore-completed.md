# Baseline (no-skill) response: cross-region-restore-completed

This file captures what a generic assistant produces WITHOUT the
backup-cross-region-operator skill loaded.

---

To restore from the DR region:

```bash
aws backup start-restore-job \
  --recovery-point-arn arn:aws:backup:us-west-2:111111111111:recovery-point:5-6-7-8 \
  --metadata '{"InstanceId":"i-restored-xregion","SubnetId":"subnet-xyz","SecurityGroupIds":"sg-xyz","InstanceType":"t3.medium"}' \
  --iam-role-arn arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole \
  --resource-type EC2 \
  --region us-west-2
```

Check the status with `describe-restore-job`.
