# Baseline (no-skill) — drift-detection-managed-execution

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses managed execution,
> the difference between on-demand and continuous drift detection,
> the auto-reconciliation behavior, and the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

To enable drift detection on your StackSet:

```bash
aws cloudformation detect-stack-set-drift \
  --stack-set-name guardduty-baseline
```

You can also update the StackSet to add auto-deployment:

```bash
aws cloudformation update-stack-set \
  --stack-set-name guardduty-baseline \
  --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false
```

Check drift status with describe-stack-set.
