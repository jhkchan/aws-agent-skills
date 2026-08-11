# Baseline (no-skill) — consolidated-billing-budget-account

> This is the response a model produces **without** the skill
> definition. It misses the per-account Cost Explorer opt-in, the
> alternate-contacts API (`aws account put-alternate-contact`), the
> consolidated-billing-does-not-mean-budgets-are-automatic caveat,
> and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

To create the account with consolidated billing:

1. Create the account:
```bash
aws organizations create-account \
  --email "aws+marketing@yourdomain.com" \
  --account-name "marketing-sandbox-use1"
```

2. Billing is consolidated automatically since it's a member account.
3. Set up a budget in the console.

That should cover it.
