# Baseline (no-skill) response: manual-gap-billing-activation

This file captures what a generic assistant produces WITHOUT the
tag-governance-automator skill loaded.

---

To activate cost allocation tags, go to the Billing console and find
the Cost Allocation Tags section. You can activate user-defined tags
there.

The tags should start appearing in Cost Explorer within 24 hours.

If you want to do it via the API, you can use:

```
aws ce update-cost-allocation-tags-status ...
```

If that API returned AccessDenied, you might need to check your IAM
permissions. Otherwise, just use the console.
