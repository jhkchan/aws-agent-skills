# Baseline (no-skill) — api-asset-live-access

> This is the response a model produces **without** the skill
> definition. It attempts to export the API asset to S3 (API assets
> are accessed LIVE, not exported), misses the Data Exchange signing
> key authentication requirement, and omits rate-limiting and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Export the API asset to S3:

```bash
aws dataexchange create-job \
  --type EXPORT_ASSETS_TO_S3 \
  --details '{"ExportAssetsToS3": {"DataSetId": "ds-api456", "RevisionId": "r-api111"}}'
```

Then access the data from your S3 bucket using curl or an HTTP client.
