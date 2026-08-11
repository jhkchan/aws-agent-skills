# Baseline (no-skill) response: multi-region-replica-deletion

This file captures what a generic assistant produces WITHOUT the
kms-key-rotation-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, per-region replica cost
analysis, regional CloudTrail verification, CONFIRM gate).

---

You have a multi-region KMS key with replicas in 4 regions but only 2
are actually being used. The replicas in ap-southeast-1 and sa-east-1
have zero API calls.

You can delete those replicas to save $2/month ($1 per region):

```
aws kms schedule-key-deletion --key-id <ap-southeast-1-replica-id> --pending-window-in-days 7
aws kms schedule-key-deletion --key-id <sa-east-1-replica-id> --pending-window-in-days 7
```

Make sure no resources in those regions are using the key first.
