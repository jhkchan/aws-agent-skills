# Baseline (no-skill) — aurora-proxy-iam-auth-tls

> This is the response a model produces **without** the skill
> definition. It creates the proxy but misses the IAM-auth-requires-TLS
> coupling, the Secrets Manager secret format verification, the rotation
> pairing benefit, the proxy-endpoint-vs-cluster-endpoint distinction,
> and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the proxy:

```bash
aws rds create-db-proxy \
  --db-proxy-name my-app-proxy \
  --engine-family POSTGRESQL \
  --role-arn arn:aws:iam::123456789012:role/rds-proxy-role
```

Then point your application at the cluster.
