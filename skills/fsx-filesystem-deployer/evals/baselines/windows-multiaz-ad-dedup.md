# Baseline (no-skill) — windows-multiaz-ad-dedup

> This is the response a model produces **without** the skill
> definition. It creates the file system but misses the Multi-AZ
> vs Single-AZ failover semantics (deployment type cannot be
> changed), the throughput capacity step sizing (throughput is
> stepped not arbitrary), the dedup savings estimation, the KMS key
> immutability, and the READY_TO_DEPLOY checklist format. Generated
> for with-skill-vs-baseline comparison.

---

Create the FSx for Windows file system:

```bash
aws fsx create-file-system \
  --file-system-type WINDOWS \
  --storage-capacity 1024 \
  --subnet-ids subnet-aaa111 subnet-bbb222
```

Then enable dedup and configure backups.
