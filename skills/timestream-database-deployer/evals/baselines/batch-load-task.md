# Baseline (no-skill) — batch-load-task

> This is the response a model produces **without** the skill
> definition. It creates the table but does not create the batch load
> task, does not note the CSV format requirements or the asynchronous
> task stages, and does not emit the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Here are the basic commands:

```bash
aws timestream-write create-database --database-name HistoricalData
aws timestream-write create-table --database-name HistoricalData --table-name SensorArchive
```

Then you can load data into the table.
