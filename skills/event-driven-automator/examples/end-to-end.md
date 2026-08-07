# End-to-end usage scenario: event-driven-automator

A walkthrough showing the skill designing two event-driven workflows
for the same account: an AUTOMATED GuardDuty-to-Lambda auto-remediation
and a MANUAL_STEP_REQUIRED S3-object-triggered pipeline with missing
DLQ and idempotency. Demonstrates the DLQ/idempotency gate and the
circular-dependency check.

## Input (user prompt)

> Design two workflows: (1) high-severity GuardDuty findings trigger
> a Lambda to isolate the EC2 instance; (2) S3 object-created events
> trigger an upload-processing Lambda.

```
Design reference: prod-event-driven-rollout
Account: 111111111111
Region: us-east-1

Workflow 1: GuardDuty auto-remediation
  Source: aws.guardduty GuardDuty Finding, severity >= 7
  Target: Lambda isolate-instance (idempotent on finding-id, tested)
  DLQ: arn:aws:sqs:us-east-1:111111111111:eventbridge-guardduty-dlq (created)

Workflow 2: S3 upload processing
  Existing rule: s3-object-created-trigger on default bus
  Target: Lambda process-upload (NO DLQ; NO idempotency check)
  CloudWatch shows duplicate invocations on the same S3 object.
```

## Skill output

```text
ARCHITECTURE: prod-event-driven-rollout (workflow 1)
BUS: default
PATTERN: source=aws.guardduty, detail-type=GuardDuty Finding, detail.severity>=7
TARGETS:
  - Lambda isolate-instance (arn:aws:lambda:us-east-1:111111111111:function:isolate-instance)
    RetryPolicy: 3 attempts, 900s max age (fail-fast for security)
    DeadLetterConfig: arn:aws:sqs:us-east-1:111111111111:eventbridge-guardduty-dlq
RETRY: 3 attempts / 15 min
SAFETY: DLQ attached, idempotency via finding-id in DynamoDB, circular-dep check PASS (Lambda publishes no events)
AUDIT: CloudTrail on lambda:InvokeFunction; CloudWatch alarm on DLQ depth; TestEventPattern validated.
VERDICT: AUTOMATED
GAP: None
TEMPLATE:
  aws events put-rule --name guardduty-high-severity --event-bus-name default --event-pattern '{"source":["aws.guardduty"],"detail-type":["GuardDuty Finding"],"detail":{"severity":[{"numeric":[">=",7]}]}}'
  aws events put-targets --rule guardduty-high-severity --event-bus-name default --targets '[{"Id":"isolate-instance","Arn":"arn:aws:lambda:us-east-1:111111111111:function:isolate-instance","DeadLetterConfig":{"Arn":"arn:aws:sqs:us-east-1:111111111111:eventbridge-guardduty-dlq"},"RetryPolicy":{"MaximumRetryAttempts":3,"MaximumEventAgeInSeconds":900}}]'
  aws lambda add-permission --function-name isolate-instance --statement-id EventBridgeInvoke-guardduty-high-severity --action lambda:InvokeFunction --principal events.amazonaws.com --source-arn arn:aws:events:us-east-1:111111111111:rule/default/guardduty-high-severity --source-account 111111111111

ARCHITECTURE: prod-event-driven-rollout (workflow 2)
BUS: default
PATTERN: source=aws.s3, detail-type=Object Created
TARGETS:
  - Lambda process-upload (no DeadLetterConfig, default RetryPolicy)
RETRY: defaults (185 attempts / 24h) — too aggressive for an upload processor
SAFETY: NO DLQ (silent event loss on Lambda failure); idempotency NOT IMPLEMENTED (duplicate invocations visible in CloudWatch); circular-dep check N/A.
AUDIT: NO CloudWatch alarm on DLQ.
VERDICT: MANUAL_STEP_REQUIRED
GAP: (1) No DLQ on Lambda target — failed invocations are silently dropped after 24h of retries. (2) No idempotency — S3 and EventBridge are both at-least-once; duplicate invocations are expected, not anomalous. Implement dedup on detail.bucket.name + detail.object.key + detail.object.eTag in DynamoDB with a conditional write. (3) No CloudWatch alarm on DLQ depth. Fix all three gaps before treating this workflow as production-ready.
TEMPLATE: (incomplete — fix GAPs first)
```

**Account-level aggregate verdict: AUTOMATED for GuardDuty + MANUAL_STEP_REQUIRED
for S3 upload processing.** Roll out the GuardDuty workflow immediately;
the S3 workflow requires DLQ and idempotency fixes first.

## What the skill caught that a generic assistant misses

1. **The DLQ gate.** A generic assistant wires the S3 Lambda without
   DLQ. The skill refuses — silent event loss is the most common
   production failure mode for EventBridge workflows.

2. **The idempotency requirement.** A generic assistant treats
   duplicate CloudWatch invocations as anomalous. The skill notes
   that EventBridge is at-least-once and S3 retries on its own;
   duplicates are expected, so idempotency on
   `bucket + key + etag` is the fix.

3. **The retry-policy tuning.** A generic assistant uses defaults
   (185 retries / 24h). The skill tunes the GuardDuty workflow to
   3 attempts / 15 min (fail-fast for security) and flags the S3
   workflow's defaults as too aggressive for an upload processor.

4. **The circular-dependency check.** A generic assistant wires
   workflows in isolation. The skill maps the rule graph for both
   workflows and confirms neither Lambda publishes events that
   could create a cycle.

5. **The Lambda invocation permission.** A generic assistant omits
   `lambda:AddPermission` for `events.amazonaws.com`. The skill
   includes it explicitly in the TEMPLATE — a missing permission
   is the most common silent non-delivery failure.

## Slash-command invocation

```
/aws:automate-event-driven-architecture
```

Or via the orchestrator:

```
/aws:pipeline
You: "design event-driven workflow for GuardDuty"
```

## CLI routing

```bash
node cli/bin/cli.js route "design EventBridge architecture"
# [Phase: Automate | Skills routed: event-driven-automator]
```

## Live-account invocation (requires AWS CLI)

```bash
# Discover existing rules on the bus
aws events list-rules --event-bus-name default --region us-east-1 --profile default

# Check targets and DLQ for a specific rule
aws events list-targets-by-rule --rule <rule> --event-bus-name default \
  --region us-east-1 --profile default

# Verify Lambda invocation permission
aws lambda get-policy --function-name <fn> \
  --query 'Policy' --output text --profile default \
  | jq '.Statement[] | select(.Principal.Service=="events.amazonaws.com")'

# Test an event pattern against a sample event
aws events test-event-pattern \
  --event-pattern file://pattern.json \
  --event file://sample-event.json \
  --region us-east-1 --profile default

# Check DLQ depth
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/<dlq> \
  --attribute-names ApproximateNumberOfMessagesVisible \
  --query 'Attributes.ApproximateNumberOfMessagesVisible' \
  --output text --profile default

# Discover existing Pipes
aws pipes list-pipes --region us-east-1 --profile default \
  --query 'Pipes[].Name'

# Discover existing Scheduler schedules
aws scheduler list-schedules --region us-east-1 --profile default \
  --query 'Schedules[].Name'
```

Then paste the output into the skill for architecture design.
