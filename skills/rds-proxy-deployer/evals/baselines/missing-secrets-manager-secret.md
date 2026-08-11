# Baseline (no-skill) — missing-secrets-manager-secret

> This is the response a model produces **without** the skill
> definition. It creates the proxy referencing a nonexistent Secrets
> Manager secret without flagging the gap. The proxy will enter
> Unavailable status when health checks fail. Does not emit a
> PREREQUISITES_MISSING verdict. Generated for with-skill-vs-baseline
> comparison.

---

Create the proxy:

```bash
aws rds create-db-proxy \
  --db-proxy-name my-broken-proxy \
  --auth '[{"SecretArn":"arn:aws:secretsmanager:us-east-1:123456789012:secret:rds/nonexistent-secret"}]'
```

The proxy should connect to the database automatically.
