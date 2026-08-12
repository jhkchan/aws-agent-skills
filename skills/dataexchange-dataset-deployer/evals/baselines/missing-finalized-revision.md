# Baseline (no-skill) — missing-finalized-revision

> This is the response a model produces **without** the skill
> definition. It proceeds to create the export job without flagging
> that the revision is in DRAFT state (unfinalized). The export job
> will fail silently because only FINALIZED revisions can be
> exported. Generated for with-skill-vs-baseline comparison.

---

Create the export job:

```bash
aws dataexchange create-job \
  --type EXPORT_ASSETS_TO_S3 \
  --details '{"ExportAssetsToS3": {"DataSetId": "ds-broken456", "RevisionId": "r-draft999"}}'
```

The data should appear in your bucket shortly.
