# Baseline (no-skill) — compliance-remediation-association

> This is the response a model produces **without** the skill
> definition. It creates the association but does not flag idempotency
> as a prerequisite for remediation, omits the EventBridge rule
> pattern for NON_COMPLIANT, and skips the OPERATION_COMPLETED
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create the inventory association:

```bash
aws ssm create-association \
  --name AWS-GatherSoftwareInventory \
  --targets "Key=tag:Environment,Values=production" \
  --schedule-expression "rate(30 minutes)" \
  --region us-east-1
```

You can set up a CloudWatch Events rule to re-trigger it if it ever
shows non-compliant.
