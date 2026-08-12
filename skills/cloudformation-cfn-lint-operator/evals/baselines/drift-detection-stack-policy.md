# Baseline (no-skill) — drift-detection-stack-policy

> This is the response a model produces **without** the skill
> definition. It runs drift detection but does not mention stack
> policy enforcement, does not interpret the drift status result
> (IN_SYNC vs DRIFTED), does not explain the difference between
> stack policies (UPDATE protection) and DeletionPolicy (DELETE
> protection), and lacks the OPERATION_COMPLETED checklist format.
> Generated for with-skill-vs-baseline comparison.

---

To check for drift:

```bash
aws cloudformation detect-stack-drift --stack-name my-infra-stack
```

You can also set a stack policy.
