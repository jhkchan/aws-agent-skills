# Baseline (no-skill) — reactive-rds-failover-investigation

> This is the response a model produces **without** the skill definition.
> It follows the DevOps Guru recommendation to "investigate recent
> deployments" even though no deployment occurred, and misses the AWS
> Health Dashboard correlation. Generated for with-skill-vs-baseline
> comparison.

---

The insight reports an RDS Multi-AZ failover. DevOps Guru recommends
investigating recent deployments. Here's what to check:

1. Check recent deployments:
```bash
aws deploy list-deployments --application-name my-app
```

2. Check the RDS cluster status:
```bash
aws rds describe-db-clusters --db-cluster-identifier aurora-prod-cluster
```

3. Review the RDS event subscription for failover events.

4. If a deployment caused the failover, roll it back.

The failover should be automatic and the cluster should be healthy
on the secondary AZ.
