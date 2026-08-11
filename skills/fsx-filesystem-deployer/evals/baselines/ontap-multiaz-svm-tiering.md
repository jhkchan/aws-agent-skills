# Baseline (no-skill) — ontap-multiaz-svm-tiering

> This is the response a model produces **without** the skill
> definition. It creates the ONTAP file system but misses the SVM
> creation step (required for multi-protocol access), the volume
> tiering configuration (without tiering, all data stays on the
> expensive SSD cache), the storage efficiency option, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Create the FSx for ONTAP file system:

```bash
aws fsx create-file-system \
  --file-system-type ONTAP \
  --storage-capacity 1024 \
  --subnet-ids subnet-eee555 subnet-fff666
```

Then create volumes.
