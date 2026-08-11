# Baseline (no-skill) response: create-global-table-ready

This file captures what a generic assistant produces WITHOUT the
dynamodb-global-tables-operator skill loaded.

---

To create a global table, you need to use the create-global-table
command:

```bash
aws dynamodb create-global-table \
  --global-table-name sessions-prod \
  --replication-group '[{"RegionName":"us-east-1"},{"RegionName":"eu-west-1"}]'
```

Make sure both tables already exist in each region with the same schema.
After creating the global table, data will automatically replicate
between the regions. You should also enable PITR in both regions for
backup purposes.
