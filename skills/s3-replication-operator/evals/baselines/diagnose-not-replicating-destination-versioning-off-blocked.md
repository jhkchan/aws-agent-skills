# Baseline (no-skill) response: diagnose-not-replicating-destination-versioning-off-blocked

This file captures what a generic assistant produces WITHOUT the
s3-replication-operator skill loaded.

---

Your replication rule shows `Status: Enabled` but objects are not
arriving at the destination. Check that the IAM role has
`s3:ReplicateObject` on the destination bucket and that the KMS key
policies grant the role.

To re-trigger replication on stuck objects, you can run a Batch
Operations job or re-PUT the objects. Verify the rule is enabled:

```bash
aws s3api get-bucket-replication --bucket prod-logs-source-us-east-1
```

If the role has the right permissions, try removing and re-adding the
rule.
