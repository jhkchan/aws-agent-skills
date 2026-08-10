# Baseline (no-skill) — aurora-serverless-v2-capacity

> This is the response a model produces **without** the skill definition.
> It creates a cluster parameter group but uses absolute memory values
> (e.g., shared_buffers=2GB) instead of formula syntax, which would cause
> OOM at minimum ACU. It also tries to set capacity in the parameter group
> rather than via ServerlessV2ScalingConfiguration on the cluster.

---

Create an Aurora Serverless v2 parameter group:

```bash
aws rds create-db-cluster-parameter-group \
  --db-cluster-parameter-group-name slsv2-pg15-params \
  --db-parameter-group-family aurora-postgresql15 \
  --description "Serverless v2 params"
```

Set shared_buffers=2GB, work_mem=4MB, and max_connections=200.
Configure scaling on the cluster.
