# Baseline (no-skill) response: dlm-policy-create-ready

This file captures what a generic assistant produces WITHOUT the
ec2-backup-operator skill loaded.

---

You can create a DLM lifecycle policy with:

```bash
aws dlm create-lifecycle-policy \
  --description "Daily snapshots of volumes tagged BackupSchedule=daily" \
  --state ENABLED \
  --execution-role-arn arn:aws:iam::111111111111:role/service-role/AWS-DLM-LifeCycleRole \
  --policy-details file://policy-details.json
```

The policy will run daily at 03:00 UTC and retain 7 snapshots.
