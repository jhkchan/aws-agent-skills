# Baseline (no-skill) — provisioned-autoscaling

> This is the response a model produces **without** the skill
> definition. It creates the table with provisioned capacity but misses
> the auto-scaling target tracking configuration (Application Auto
> Scaling service-namespace cassandra), the scale-out vs scale-in
> cooldown asymmetry, the fact that auto-scaling must be registered
> separately for read and write capacity dimensions, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Create the table with provisioned capacity:

```bash
aws keyspaces create-table \
  --keyspace-name telemetry_keyspace \
  --table-name sensor_readings \
  --schema-definition '{"allColumns": [...], "partitionKeys": [{"name": "sensor_id", "type": "text"}]}' \
  --capacity-spec '{"throughputMode": "PROVISIONED", "provisionedThroughput": {"readCapacityUnits": 500, "writeCapacityUnits": 1000}}'
```

Then set up auto-scaling. The capacity will adjust automatically.
