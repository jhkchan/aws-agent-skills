# Baseline (no-skill) — magnetic-store-write-s3

> This is the response a model produces **without** the skill
> definition. It creates the table but does not flag the S3 bucket
> policy requirement, does not configure magnetic store write
> properties explicitly, and does not emit the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create the database and table:

```bash
aws timestream-write create-database --database-name IoTSensorData
aws timestream-write create-table --database-name IoTSensorData --table-name EventLogs
```

Then set retention and you should be good.
