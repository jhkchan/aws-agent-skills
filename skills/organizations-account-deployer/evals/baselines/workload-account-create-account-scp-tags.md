# Baseline (no-skill) — workload-account-create-account-scp-tags

> This is the response a model produces **without** the skill
> definition. It misses the SCP-must-be-enabled-on-root prerequisite,
> the OU-inheritance model (it attaches at account level instead),
> the consolidated-billing-does-not-mean-Cost-Explorer-is-automatic
> caveat, the immutable-IAM-role-name constraint, and the
> READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

To create a member account:

1. Create the account:
```bash
aws organizations create-account \
  --email "aws+analytics@yourdomain.com" \
  --account-name "analytics-pipeline-use1"
```

2. Attach an SCP to the account:
```bash
aws organizations attach-policy \
  --policy-id <scp-id> \
  --target-id <account-id>
```

3. Billing is automatic since the account is in the org.
