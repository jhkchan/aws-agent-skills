# Baseline (no-skill) response: glacier-retrieval-mismatch

This file captures what a generic assistant produces WITHOUT the
s3-storage-class-optimizer skill loaded.

---

You have 18 TB in Deep Archive but you're retrieving 15% of it per
month. That's a lot of retrieval fees. Deep Archive is meant for data
you rarely access.

You might want to move some of that data back to a warmer tier. You
could update your lifecycle policy to use Glacier Flexible Retrieval
instead of Deep Archive, or even Standard-IA if you access it that
frequently.

The retrieval costs at $55/month are significant. You'd need to
compare that against the storage savings to see if Deep Archive is
still worth it.

You can update the lifecycle policy:

```
aws s3api put-bucket-lifecycle-configuration \
  --bucket bucket-glacier-retrieval-mismatch \
  --lifecycle-configuration file://updated-lifecycle.json
```
