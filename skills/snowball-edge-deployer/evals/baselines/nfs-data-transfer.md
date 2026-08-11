# Baseline (no-skill) — nfs-data-transfer

> This is the response a model produces **without** the skill
> definition. It mentions mounting NFS but misses the critical
> start-service step (NFS does not auto-start), does not provide a
> parallel copy strategy, and omits the READY_TO_DEPLOY checklist.
> Generated for with-skill-vs-baseline comparison.

---

Mount the NFS share and copy data:

```bash
mount -t nfs 192.168.1.100:/nfs/path /mnt/snowball
cp -r /data/* /mnt/snowball/
```

This should copy your data to the device.
