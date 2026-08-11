# Baseline (no-skill) — windows-singleaz-throughput

> This is the response a model produces **without** the skill
> definition. It creates the file system but misses the throughput
> capacity step sizing (picks 180 directly instead of the nearest
> valid step), the cost trade-off of Single-AZ vs Multi-AZ, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Create the FSx for Windows file system:

```bash
aws fsx create-file-system \
  --file-system-type WINDOWS \
  --storage-capacity 512 \
  --storage-type HDD \
  --subnet-ids subnet-aaa111
```

Throughput 180 MB/s.
