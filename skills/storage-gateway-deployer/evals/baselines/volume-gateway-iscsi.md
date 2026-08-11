# Baseline (no-skill) — volume-gateway-iscsi

> This is the response a model produces **without** the skill
> definition. It lists the create-volume command but misses that cached
> mode requires BOTH a cache and upload buffer (treats them as one),
> does not mention iSCSI initiator connection details, and omits the
> READY_TO_DEPLOY checklist. Generated for with-skill-vs-baseline
> comparison.

---

Create the volume gateway and add an iSCSI volume:

```bash
aws storagegateway activate-gateway \
  --activation-key VWXYZ-98765-QRSTU-43210-PQRSX \
  --gateway-name prod-volume-gateway \
  --gateway-type VOLUME

aws storagegateway create-cached-iscsi-volume \
  --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-XXXXX \
  --volume-size-in-bytes 1073741824000 \
  --target-name prod-volume-01
```

Then connect your iSCSI initiator.
