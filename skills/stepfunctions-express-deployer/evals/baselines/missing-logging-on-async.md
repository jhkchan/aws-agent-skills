# Baseline (no-skill) — missing-logging-on-async

> This is the response a model produces **without** the skill definition.
> It provisions the async Express workflow as requested (without
> logging), so the first failure is invisible — the 5-min execution
> history rolls over and there is no alarm. The operator cannot debug
> failures and discovers the issue only after a customer complaint.
> Generated for with-skill-vs-baseline comparison.

---

To create the async Express workflow:

1. Create the state machine:
```bash
aws stepfunctions create-state-machine \
  --name batch-loader \
  --definition file://definition.json \
  --role-arn arn:aws:iam::123456789012:role/batch-loader-role \
  --type EXPRESS
```

2. Configure EventBridge:
```bash
aws events put-rule --name batch-loader-schedule \
  --schedule-expression "rate(1 minute)"
aws events put-targets --rule batch-loader-schedule \
  --targets 'Id=1,Arn=arn:aws:states:us-east-1:123456789012:stateMachine:batch-loader,RoleArn=arn:aws:iam::123456789012:role/events-target-role'
```

The workflow runs every minute.
