# Baseline (no-skill) — standard-account-vending

> This is the response a model produces **without** the skill
> definition. It creates the account via raw Organizations CreateAccount
> instead of the Account Factory Service Catalog product (missing
> Guardrails, baselines, SSO enrollment), does not verify OU registration,
> does not provision the permission set after assignment, and does not
> emit the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the account:

```bash
aws organizations create-account \
  --email aws+prod-data-platform@company.com \
  --account-name data-platform-prod
```

Then assign SSO and move to the OU.
