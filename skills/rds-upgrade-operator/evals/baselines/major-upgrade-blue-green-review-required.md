# Baseline (no-skill) response: major-upgrade-blue-green-review-required

This file captures what a generic assistant produces WITHOUT the
rds-upgrade-operator skill loaded.

---

To upgrade Aurora MySQL from 5.7 to 8.0, you can use a blue/green
deployment:

```bash
aws rds create-blue-green-deployment \
  --blue-green-deployment-name prod-payments-bg \
  --source arn:aws:rds:us-east-1:111111111111:cluster:prod-payments-cluster \
  --target-engine-version 8.0.mysql_aurora.3.04.0
```

Wait for the green environment to be ready, then switch over:

```bash
aws rds switchover-blue-green-deployment \
  --blue-green-deployment-id <bg-id>
```

Make sure your application is compatible with MySQL 8.0 before
switching.
