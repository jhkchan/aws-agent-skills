# End-to-end usage scenario: eventbridge-rule-deployer

A walkthrough showing the skill deploying two EventBridge rule
workflows for the same account: a READY_TO_DEPLOY GuardDuty-to-
Lambda auto-remediation and a PREREQUISITES_MISSING CodeBuild-
to-Slack notification missing DLQ and idempotency. Demonstrates
the 5-point deployment gate and the PREREQUISITES checklist.

## Input (user prompt)

> Deploy two EventBridge rules: (1) high-severity GuardDuty
> findings trigger a Lambda to isolate the EC2 instance; (2)
> CodeBuild build failures trigger a Slack notification Lambda.

```
Design reference: prod-rule-deploy-rollout
Account: 111111111111
Region: us-east-1

Workflow 1: GuardDuty auto-remediation
  Source: aws.guardduty GuardDuty Finding, severity >= 7
  Target: Lambda isolate-instance (idempotent on finding-id, tested)
  DLQ: arn:aws:sqs:us-east-1:111111111111:eventbridge-guardduty-dlq
    (created with 14-day retention).
  Lambda invocation permission: granted.

Workflow 2: CodeBuild failure notification
  Source: aws.codebuild CodeBuild Build State Change, FAILED
  Target: Lambda notify-slack (NOT idempotent)
  DLQ: NONE (not yet created)
  Lambda invocation permission: granted.
```

## Skill output

```text
PLAN: prod-rule-deploy-rollout (workflow 1)
RULE:
  Name: guardduty-high-severity
  Bus: default
  Type: event-pattern
  Pattern: source=aws.guardduty, detail-type=GuardDuty Finding, detail.severity>=7
  State: ENABLED
TARGETS:
  - isolate-instance (Lambda): arn:aws:lambda:us-east-1:111111111111:function:isolate-instance
    RetryPolicy: 3 attempts / 900s max age (fail-fast for security)
    DeadLetterConfig: arn:aws:sqs:us-east-1:111111111111:eventbridge-guardduty-dlq
    InputTransformer: no (Lambda handles full event)
    InvocationPermission: verified
RETRY: 3 attempts / 15 min
DLQ: eventbridge-guardduty-dlq (14-day retention)
INPUT_TRANSFORM: full event
CROSS_ACCOUNT: none
PREREQUISITES:
  [x] Pattern validated via TestEventPattern
  [x] Target exists and ARN verified
  [x] DLQ exists with 14-day retention
  [x] Lambda invocation permission granted
  [x] CloudWatch alarm on DLQ depth configured
  [x] Idempotency: consumer dedupes on detail.id (finding ID)
VERDICT: READY_TO_DEPLOY
GAP: None
TEMPLATE:
  aws events put-rule --name guardduty-high-severity --event-bus-name default --event-pattern '{"source":["aws.guardduty"],"detail-type":["GuardDuty Finding"],"detail":{"severity":[{"numeric":[">=",7]}]}}' --state ENABLED
  aws events put-targets --rule guardduty-high-severity --event-bus-name default --targets '[{"Id":"isolate-instance","Arn":"arn:aws:lambda:us-east-1:111111111111:function:isolate-instance","DeadLetterConfig":{"Arn":"arn:aws:sqs:us-east-1:111111111111:eventbridge-guardduty-dlq"},"RetryPolicy":{"MaximumRetryAttempts":3,"MaximumEventAgeInSeconds":900}}]'

PLAN: prod-rule-deploy-rollout (workflow 2)
RULE:
  Name: codebuild-failed
  Bus: default
  Type: event-pattern
  Pattern: source=aws.codebuild, detail-type=CodeBuild Build State Change, detail.build-status=FAILED
  State: ENABLED
TARGETS:
  - notify-slack (Lambda): arn:aws:lambda:us-east-1:111111111111:function:notify-slack
    RetryPolicy: defaults (185 attempts / 24h) — too aggressive for notification
    DeadLetterConfig: NONE
    InputTransformer: no
    InvocationPermission: verified
RETRY: defaults (185 / 24h) — should be 3 / 900s
DLQ: NONE — silent event loss on Lambda failure
INPUT_TRANSFORM: full event
PREREQUISITES:
  [x] Pattern validated via TestEventPattern
  [x] Target exists and ARN verified
  [ ] DLQ missing — create eventbridge-codebuild-failed-dlq
  [x] Lambda invocation permission verified
  [ ] CloudWatch alarm on DLQ depth not configured
  [ ] Idempotency: consumer does NOT dedup; CodeBuild emits multiple state-change events per build
VERDICT: PREREQUISITES_MISSING
GAP: (1) DLQ not configured — failed invocations will be silently dropped after retry exhaustion. (2) Default retry policy (185 attempts / 24h) is too aggressive for a Slack notification; should be 3 attempts / 900s. (3) No idempotency — CodeBuild emits multiple state-change events per build (STARTED, IN_PROGRESS, FAILED, FAILED-retry); the Lambda will post duplicate Slack messages without dedup on detail.build-id + detail.build-status. Address all three before deployment.
TEMPLATE: (incomplete — fix GAPs first)
```

**Account-level aggregate verdict: READY_TO_DEPLOY for GuardDuty +
PREREQUISITES_MISSING for CodeBuild notification.** Deploy the
GuardDuty workflow now; the CodeBuild workflow requires DLQ creation,
retry tuning, and idempotency before deployment.

## What the skill caught that a generic assistant misses

1. **The DLQ gate.** A generic assistant wires the CodeBuild Lambda
   without DLQ. The skill refuses — silent event loss is the most
   common production failure mode for EventBridge rules.

2. **The retry-policy tuning.** A generic assistant uses defaults
   (185 retries / 24h). The skill tunes the GuardDuty workflow to
   3 attempts / 900s (fail-fast for security) and flags the
   CodeBuild workflow's defaults as too aggressive for a Slack
   notification.

3. **The idempotency note.** A generic assistant treats duplicate
   CloudWatch invocations as anomalous. The skill flags the
   CodeBuild Lambda as missing idempotency and recommends dedup on
   `detail.build-id + detail.build-status`.

4. **The Lambda invocation permission.** A generic assistant omits
   `lambda:AddPermission` for `events.amazonaws.com`. The skill
   includes it explicitly in the pre-flight checklist — a missing
   permission is the most common silent non-delivery failure.

5. **The pre-flight safety checks.** A generic assistant emits a
   plan; the skill emits a 5-point deployment gate (pattern
   validates, target ARNs resolve, DLQ exists with 14-day
   retention, invocation permissions granted, consumer idempotency
   noted). Any miss is a specific GAP.

## Slash-command invocation

```
/aws:deploy-eventbridge-rule
```

Or via the orchestrator:

```
/aws:pipeline
You: "deploy EventBridge rule for GuardDuty"
```

## CLI routing

```bash
node cli/bin/cli.js route "deploy EventBridge rule"
# [Phase: Deploy | Skills routed: eventbridge-rule-deployer]
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

# Describe existing event buses
aws events list-event-buses --region us-east-1 --profile default

# Verify cross-account bus policy
aws events describe-event-bus --name <bus> \
  --query 'Policy' --profile default
```

Then paste the output into the skill for deployment plan generation.
