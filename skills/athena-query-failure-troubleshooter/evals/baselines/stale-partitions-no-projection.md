# Baseline (no-skill) response: stale-partitions-no-projection

This file captures what a generic assistant produces WITHOUT the
athena-query-failure-troubleshooter skill loaded.

---

Your Athena query returns zero rows even though the data exists on
S3. This is likely because Athena doesn't know about the new
partitions. You need to run MSCK REPAIR TABLE to load the partition
metadata:

```sql
MSCK REPAIR TABLE analytics.events_daily;
```

After running this, the new partitions should be visible and your
query should return data. If MSCK REPAIR takes too long, you can
manually add partitions with ALTER TABLE ADD PARTITION.
