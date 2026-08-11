# Baseline (no-skill) — multi-az-failover-security-groups

> This is the response a model produces **without** the skill
> definition. It creates the proxy but misses the database security
> group ingress rule (the #1 forgotten network configuration), the
> failover handling benefit (proxy reroutes on Aurora writer failover),
> and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the proxy:

```bash
aws rds create-db-proxy \
  --db-proxy-name ha-proxy \
  --vpc-subnet-ids subnet-aaa subnet-bbb subnet-ccc
```

The proxy should be highly available now.
