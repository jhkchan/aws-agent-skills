# Baseline (no-skill) — express-distributed-map-logging

> This is the response a model produces **without** the skill definition.
> It creates the state machine but omits the loggingConfiguration (so
> async executions are invisible after the 5-min history rolls over),
> sets MaxConcurrency too high for the 5-min cap without verifying
> duration, and skips the CloudWatch alarm on ExecutionsFailed.
> Generated for with-skill-vs-baseline comparison.

---

To create the Express workflow with Distributed Map:

1. Create the IAM role with lambda:InvokeFunction permissions.

2. Create the state machine:
```bash
aws stepfunctions create-state-machine \
  --name order-processor \
  --definition file://definition.json \
  --role-arn arn:aws:iam::123456789012:role/order-processor-role \
  --type EXPRESS
```

3. Configure EventBridge:
```bash
aws events put-rule --name order-processor-schedule \
  --schedule-expression "rate(5 minutes)"
aws events put-targets --rule order-processor-schedule \
  --targets 'Id=1,Arn=arn:aws:states:us-east-1:123456789012:stateMachine:order-processor,RoleArn=arn:aws:iam::123456789012:role/events-target-role'
```

The workflow is ready to process orders every 5 minutes.
