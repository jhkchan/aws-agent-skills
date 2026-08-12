# Baseline (no-skill) — rds-failover-experiment

> This is the response a model produces **without** the skill
> definition. It shows the failover action but misses scoping the
> IAM role to rds:FailoverDBCluster on the specific cluster ARN,
> does not flag the stop condition as a safety net, and does not
> emit the READY_TO_DEPLOY checklist. Generated for with-skill-vs-
> baseline comparison.

---

For an RDS failover experiment:

```bash
aws fis create-experiment-template \
  --description "RDS failover test" \
  --role-arn arn:aws:iam::123456789012:role/FISExperimentRole \
  --actions file://actions.json \
  --targets file://targets.json
```

Add the aws:rds:failover-db-cluster action targeting your cluster.
