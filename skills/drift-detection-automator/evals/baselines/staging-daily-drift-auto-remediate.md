# Baseline (no-skill) response: staging-daily-drift-auto-remediate

This file captures what a generic assistant produces WITHOUT the
drift-detection-automator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, severity classification,
suppression rules, SSM Automation with approval gates, StackSet patterns).

---

You can set up drift detection for your CloudFormation stack using
AWS Config or a scheduled Lambda function. The Lambda can call
detect-stack-drift on a schedule via EventBridge.

If drift is detected, you can send an SNS notification and optionally
trigger a remediation by updating the stack.

Something like:

```
aws events put-rule --schedule-expression "cron(0 2 * * ? *)"
aws lambda create-function ...
```

For the remediation, you could use SSM Automation to run a CloudFormation
update. But you should be careful about auto-remediating in production.

I don't remember the exact API for describe-stack-resource-drifts.
You might need to check the CloudFormation docs.
