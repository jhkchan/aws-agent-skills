# Baseline (no-skill) — eventbridge-scheduled-sns-rate-control

> This is the response a model produces **without** the skill
> definition. It creates the document but does not wire the
> EventBridge rule, SNS notification configuration, or rate control
> parameters correctly. Omits the READY_TO_DEPLOY checklist.
> Generated for with-skill-vs-baseline comparison.

---

Create the SSM document:

```bash
aws ssm create-document --name NightlyPatchCheck \
  --content file://runbook.json --document-type Automation
```

Then set up EventBridge separately. You can add SNS later.
