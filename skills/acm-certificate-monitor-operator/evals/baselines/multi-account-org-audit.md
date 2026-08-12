# Baseline (no-skill) — multi-account-org-audit

> This is the response a model produces **without** the skill
> definition. It suggests checking certificates in one account but
> misses the Organizations assume-role pattern for multi-account audit,
> does not iterate across accounts, and omits the OPERATION_COMPLETED
> report format. Generated for with-skill-vs-baseline comparison.

---

To audit certificates across your accounts, you'll need to switch
profiles or assume roles in each account and run:

```bash
aws acm list-certificates --region us-east-1
```

Do this for each account. You can set up profiles in your AWS config
to make switching easier.
