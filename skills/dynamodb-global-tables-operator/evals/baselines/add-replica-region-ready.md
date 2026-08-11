# Baseline (no-skill) response: add-replica-region-ready

This file captures what a generic assistant produces WITHOUT the
dynamodb-global-tables-operator skill loaded.

---

To add eu-west-1 as a new replica, you can use the update-global-table
command:

```bash
aws dynamodb update-global-table \
  --global-table-name orders-prod \
  --replica-updates '[{"Create":{"RegionName":"eu-west-1"}}]'
```

This should create the replica in eu-west-1. You may need to wait for
the data to replicate. After that, you should be able to read and write
from eu-west-1.

Make sure your IAM role has the right permissions. Also consider
enabling PITR in the new region.
