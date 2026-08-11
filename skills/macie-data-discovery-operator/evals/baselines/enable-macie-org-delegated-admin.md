# Baseline (no-skill) — enable-macie-org-delegated-admin

> This is the response a model produces **without** the skill definition.
> It misses the org-level delegated admin workflow (management account
> vs delegated admin), the auto-enable configuration for new members,
> the pre-flight permission checks, and the VERDICT/PRE_CHECKS output
> contract. Generated for with-skill-vs-baseline comparison.

---

To enable Macie for your organization:

1. Enable Macie in each account:
```bash
aws macie2 enable-macie-session
```

2. Run this in all 5 member accounts.

That should enable Macie for your org.
