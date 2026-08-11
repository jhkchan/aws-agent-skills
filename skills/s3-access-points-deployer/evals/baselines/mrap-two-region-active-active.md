# Baseline (no-skill) — mrap-two-region-active-active

> This is the response a model produces **without** the skill definition.
> It creates the MRAP but does NOT warn about the non-backfill behavior,
> so the operator expects a global namespace over all data and gets a
> partial one. Generated for with-skill-vs-baseline comparison.

---

To create a multi-region access point:

```bash
aws s3control create-multi-region-access-point \
  --account-id 123456789012 \
  --details Name=global-assets-mrap,Regions='[{Bucket=arn:aws:s3:::assets-use1},{Bucket=arn:aws:s3:::assets-usw2}]'
```

Then check status:

```bash
aws s3control get-multi-region-access-point \
  --account-id 123456789012 \
  --name global-assets-mrap
```

Use the MRAP alias hostname in your application once status is READY.
