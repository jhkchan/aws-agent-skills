# Baseline (no-skill) — s3-export-lake-formation

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the entitlement-vs-IAM
> distinction for sharing, the Lake Formation registration step (jumps
> to table creation without registering the S3 location), the
> asynchronous job polling requirement, and the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create the export job:

```bash
aws dataexchange create-job \
  --type EXPORT_ASSETS_TO_S3 \
  --details '{"ExportAssetsToS3": {"DataSetId": "ds-abc12345", "RevisionId": "r-ghi11122"}}'
```

Then create the Glue table:

```bash
aws glue create-table \
  --database-name data_exchange_db \
  --table-input '{"Name": "market_data"}'
```

The data should be in S3 and ready to query.
