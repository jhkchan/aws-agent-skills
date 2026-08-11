# Baseline (no-skill) — database-table-scheduled-query

> This is the response a model produces **without** the skill
> definition. It creates the database and table but does not configure
> the scheduled query target table first, does not flag that the
> execution role needs query+write+SNS permissions, and does not emit
> a READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Here are the commands to set up your Timestream resources:

```bash
aws timestream-write create-database --database-name IoTSensorData
aws timestream-write create-table --database-name IoTSensorData --table-name TemperatureReadings
```

Then you can create a scheduled query if needed.
