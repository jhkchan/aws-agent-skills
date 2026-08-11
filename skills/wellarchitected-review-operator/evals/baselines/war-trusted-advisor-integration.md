# Baseline (no-skill) response: war-trusted-advisor-integration

This file captures what a generic assistant produces WITHOUT the
wellarchitected-review-operator skill loaded.

---

To use Trusted Advisor findings in a Well-Architected review,
you can pull the check result and add it as evidence:

```
aws trustedadvisor get-check-result \
  --check-id LowUtilizationEC2Resources
```

Then manually apply the findings to the cost optimization
questions in the console. You can set the risk tier based on
the TA result.
