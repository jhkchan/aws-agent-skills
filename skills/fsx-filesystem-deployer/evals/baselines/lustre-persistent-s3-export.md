# Baseline (no-skill) — lustre-persistent-s3-export

> This is the response a model produces **without** the skill
> definition. It creates the Lustre file system but misses the S3
> export semantics (S3 is the backing repository, not the file
> system), the auto-import policy configuration, the LZ4 compression
> option, the SCRATCH vs PERSISTENT durability difference, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Create the FSx for Lustre file system:

```bash
aws fsx create-file-system \
  --file-system-type LUSTRE \
  --storage-capacity 2400 \
  --subnet-ids subnet-ccc333
```

Then link S3.
