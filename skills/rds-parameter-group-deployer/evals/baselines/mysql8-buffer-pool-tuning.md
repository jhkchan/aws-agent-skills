# Baseline (no-skill) — mysql8-buffer-pool-tuning

> This is the response a model produces **without** the skill definition.
> It creates the parameter group but does not distinguish between
> static and dynamic parameters, misses the formula syntax for
> innodb_buffer_pool_size, does not specify ApplyMethod, and omits the
> association step and reboot warning for max_connections and
> character_set_server.

---

Create a MySQL parameter group:

```bash
aws rds create-db-parameter-group \
  --db-parameter-group-name orders-mysql8-params \
  --db-parameter-group-family mysql8.0 \
  --description "Orders MySQL8 params"
```

Set innodb_buffer_pool_size, max_connections, and slow_query_log.
Associate it with your DB instance.
