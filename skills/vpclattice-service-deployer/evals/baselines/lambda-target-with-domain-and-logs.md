# Baseline (no-skill) — lambda-target-with-domain-and-logs

> This is the response a model produces **without** the skill
> definition. It creates the Lambda target group but misses that the ACM
> certificate must be in us-east-1 (the Lattice-managed TLS region)
> regardless of the service's region, may not configure access log
> delivery, and does not emit the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create a Lambda target group:

```bash
aws vpc-lattice create-target-group --name tg-processor --type LAMBDA
```

Add a custom domain and some logs.
