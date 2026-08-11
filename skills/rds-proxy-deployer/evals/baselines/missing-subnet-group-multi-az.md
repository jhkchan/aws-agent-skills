# Baseline (no-skill) — missing-subnet-group-multi-az

> This is the response a model produces **without** the skill
> definition. It creates the proxy with all subnets in the same AZ
> without flagging the multi-AZ requirement. The proxy will be single-AZ
> and not highly available. Does not emit a PREREQUISITES_MISSING
> verdict. Generated for with-skill-vs-baseline comparison.

---

Create the proxy:

```bash
aws rds create-db-proxy \
  --db-proxy-name ha-proxy-broken \
  --vpc-subnet-ids subnet-aaa subnet-bbb
```

The proxy is now deployed.
