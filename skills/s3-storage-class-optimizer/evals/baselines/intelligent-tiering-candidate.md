# Baseline (no-skill) response: intelligent-tiering-candidate

This file captures what a generic assistant produces WITHOUT the
s3-storage-class-optimizer skill loaded.

---

Your bucket has 20 TB all in Standard storage with unpredictable access
patterns. Since you can't predict which objects will be accessed, you
should consider using S3 Intelligent-Tiering. It automatically moves
objects between tiers based on usage.

You can enable it with:

```
aws s3api put-bucket-intelligent-tiering-configuration \
  --bucket bucket-intelligent-tiering-candidate \
  --id ConfigID
```

There's a small monitoring fee but it might be worth it for the
automatic tiering. You'll save money on the objects that aren't
accessed frequently.
