# Baseline (no-skill) — missing-s3-bucket-policy

> This is the response a model produces **without** the skill
> definition. It creates the table and enables magnetic store writes
> without flagging that the S3 bucket lacks the required bucket
> policy, which means late-arrival writes will silently fail. Does
> not emit a PREREQUISITES_MISSING verdict. Generated for with-skill-
> vs-baseline comparison.

---

Sure, here are the commands:

```bash
aws timestream-write create-table --database-name IoTSensorData --table-name LateArrivalData
aws timestream-write update-table \
  --database-name IoTSensorData --table-name LateArrivalData \
  --magnetic-store-write-properties "EnableMagneticStoreWrites=true,MagneticStoreRejectedDataLocation=s3://my-data-bucket/"
```

That should enable late-arrival writes.
