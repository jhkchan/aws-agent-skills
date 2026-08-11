# Baseline (no-skill) — production-account-via-control-tower

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the OU-inheritance
> model for SCP/tag policy, the org-trail-only-inherits-for-new-
> accounts constraint, the Identity Center account-assignment
> requirement, the alternate-contacts API, the budget construct, and
> the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Here's how to create an AWS account:

1. Create the account:
```bash
aws organizations create-account \
  --email "aws+prod-workload@yourdomain.com" \
  --account-name "prod-workload-use1"
```

2. Add an SCP:
```bash
aws organizations attach-policy \
  --policy-id <policy-id> \
  --target-id <account-id>
```

3. Done.
