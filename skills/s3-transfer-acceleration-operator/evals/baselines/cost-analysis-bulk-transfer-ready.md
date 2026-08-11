# Baseline (no-skill) response: cost-analysis-bulk-transfer-ready

This file captures what a generic assistant produces WITHOUT the
s3-transfer-acceleration-operator skill loaded.

---

For a 50 TB transfer from Tokyo to us-east-1, Transfer Acceleration
will cost $0.025/GB x 50,000 GB = $1,250. You could also consider
Direct Connect as an alternative, which might be cheaper for large
volumes.

To enable acceleration and start the transfer:

```bash
aws s3api put-bucket-accelerate-configuration \
  --bucket migration-target \
  --accelerate-configuration Status=Enabled
```
