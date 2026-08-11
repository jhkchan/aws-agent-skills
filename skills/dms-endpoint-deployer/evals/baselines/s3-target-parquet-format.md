# Baseline (no-skill) — s3-target-parquet-format

> This is the response a model produces **without** the skill
> definition. It creates the S3 target but misses the extra connection
> attributes for Parquet format (DataFormat, CompressionType,
> EncodingType, AddColumnName), the service access role configuration,
> and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

To create a DMS S3 target endpoint:

1. Create an S3 target endpoint in DMS.
2. Specify the bucket name and folder.
3. Provide a service role with S3 access.
4. DMS will use CSV format by default.

```bash
aws dms create-endpoint --engine-name s3 --endpoint-type target \
  --s3-settings '{"BucketName":"my-dms-target-bucket"}'
```

You can change the format in the console if needed.
