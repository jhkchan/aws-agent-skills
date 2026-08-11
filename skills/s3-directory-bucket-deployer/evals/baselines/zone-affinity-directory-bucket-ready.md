# Baseline (no-skill) response: zone-affinity-directory-bucket-ready

This file captures what a generic assistant produces WITHOUT the
s3-directory-bucket-deployer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, AZ ID resolution,
name format validation, zone-affinity verification, BucketType check,
post-deploy verification commands).

---

Here's how to create an S3 Express One Zone bucket:

```bash
aws s3api create-bucket --bucket ml-cache-data --region us-east-1
```

Your EC2 instances in us-east-1a should get good latency since they're
in the same region.
