# Baseline (no-skill) response: delete-old-snapshots-lifecycle-review

This file captures what a generic assistant produces WITHOUT the
rds-snapshot-operator skill loaded.

---

To delete old snapshots, you can use the AWS CLI:

```bash
aws rds delete-db-snapshot \
  --db-snapshot-identifier dev-test-db-snap-20260701

aws rds delete-db-snapshot \
  --db-snapshot-identifier staging-db-snap-20260710

aws rds delete-db-snapshot \
  --db-snapshot-identifier prod-orders-db-snap-20260705
```

You could also automate this with a Lambda function triggered by
EventBridge on a schedule. Make sure to check if any snapshots have
compliance requirements before deleting.
