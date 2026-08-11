# Baseline (no-skill) response: war-create-workload-all-pillars

This file captures what a generic assistant produces WITHOUT the
wellarchitected-review-operator skill loaded.

---

To create a Well-Architected workload, you can use the AWS CLI:

```
aws wellarchitected create-workload \
  --workload-name checkout-service \
  --description "Checkout microservice" \
  --environment PRODUCTION \
  --lenses wellarchitected \
  --review-owner payments-platform@example.com
```

Then add pillars separately if needed. You should see the
workload in the console after creation.
