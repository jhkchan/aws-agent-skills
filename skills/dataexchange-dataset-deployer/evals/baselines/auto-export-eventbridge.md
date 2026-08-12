# Baseline (no-skill) — auto-export-eventbridge

> This is the response a model produces **without** the skill
> definition. It mentions EventBridge but misses the fact that auto-
> export is NOT a built-in Data Exchange feature — it requires a
> custom EventBridge rule + Lambda orchestration. Omits the Data
> Update event pattern, the Lambda StartJob call, and the asynchronous
> job polling. Generated for with-skill-vs-baseline comparison.

---

Enable auto-export in Data Exchange console or via CLI:

```bash
aws dataexchange create-job \
  --type EXPORT_ASSETS_TO_S3 \
  --details '{"ExportAssetsToS3": {"DataSetId": "ds-auto123"}}'
```

Set up an EventBridge rule to trigger on new data:

```bash
aws events put-rule \
  --name "DataExchangeAuto" \
  --event-pattern '{"source": ["aws.dataexchange"]}'
```

New revisions should auto-export to your bucket.
