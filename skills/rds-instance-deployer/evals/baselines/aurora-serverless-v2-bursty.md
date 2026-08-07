# Baseline (no-skill) — aurora-serverless-v2-bursty

> This is the response a model produces **without** the skill definition.
> It uses Aurora Serverless v1 (`EngineMode: serverless`) which is being
> deprecated, misses the MinCapacity=2 cold-start rationale, omits the
> cluster-level encryption and deletion protection, and lacks the
> READY_TO_DEPLOY checklist. Generated for with-skill-vs-baseline
> comparison.

---

For a bursty SaaS workload, use Aurora Serverless:

```bash
aws rds create-db-cluster \
  --db-cluster-identifier saas-tenant-db \
  --engine aurora-postgresql \
  --engine-version 16.3 \
  --engine-mode serverless \
  --master-username admin \
  --master-user-password <password> \
  --scaling-configuration MinCapacity=1,MaxCapacity=32,AutoPause=true
```

This gives you scaling with auto-pause for cost savings. After creation
you can enable Performance Insights and Enhanced Monitoring.
