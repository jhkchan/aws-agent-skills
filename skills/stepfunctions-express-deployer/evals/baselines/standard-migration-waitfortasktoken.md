# Baseline (no-skill) — standard-migration-waitfortasktoken

> This is the response a model produces **without** the skill definition.
> It converts the Standard state machine to Express without flagging the
> `.waitForTaskToken` incompatibility or the 6-minute runtime exceeding
> the 5-min cap. The create-state-machine call will fail with a
> definition-validation error, but the operator won't know why.
> Generated for with-skill-vs-baseline comparison.

---

To migrate approval-flow from Standard to Express:

1. Update the state machine type to EXPRESS:
```bash
aws stepfunctions update-state-machine \
  --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:approval-flow \
  --definition file://approval-flow.json \
  --type EXPRESS \
  --logging-configuration level=ERROR,includeExecutionData=true
```

2. Attach CloudWatch Logs at ERROR level (already done above).

3. Verify the new type:
```bash
aws stepfunctions describe-state-machine \
  --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:approval-flow
```

The migration is complete.
