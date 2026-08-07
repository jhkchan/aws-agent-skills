---
description: Design Amazon EventBridge event-driven workflows with rules, targets, DLQ, idempotency, Pipes, and Scheduler.
nl_triggers:
  - "EventBridge rule target"
  - "event-driven architecture"
  - "EventBridge Pipes"
  - "EventBridge Scheduler"
  - "event pattern matching"
  - "DLQ for events"
  - "idempotent consumer EventBridge"
  - "GuardDuty finding automation"
  - "Security Hub finding workflow"
  - "CodeBuild failure notification"
  - "EC2 state change trigger"
  - "Auto Scaling launch trigger"
  - "S3 object created trigger"
  - "CloudWatch alarm event"
  - "circular dependency EventBridge"
  - "API destination"
  - "global endpoints EventBridge"
  - "EventBridge Lambda"
  - "EventBridge Step Functions"
routes_to: event-driven-automator
---

# /aws:automate-event-driven-architecture

Activate the `event-driven-automator` skill and design an
EventBridge-driven architecture with the correct bus, pattern,
target, retry policy, DLQ, idempotency, and circular-dependency
gates.

## What it does

Reads an event source and desired action (or an existing rule/target
configuration for review), then applies a 10-step design process:

1. Choose the event bus (default / custom / partner).
2. Write the event pattern with content-based filtering.
3. Choose target type (Lambda, Step Functions, SQS, SNS, API
   destination, ECS, Systems Manager).
4. Configure retry policy and per-target DLQ.
5. Add idempotency to the consumer (DynamoDB conditional write).
6. Detect and break circular dependencies in the rule graph.
7. Use EventBridge Pipes for stream/queue sources (DynamoDB Streams,
   Kinesis, SQS, MQ, MSK).
8. Use EventBridge Scheduler for time-based triggers (preferred over
   cron-style rules).
9. Configure multi-region failover via global endpoints.
10. Audit delivery, replay via archive, and Schema Registry.

Emits a deterministic VERDICT per workflow:

```text
ARCHITECTURE: <reference>
BUS: <bus-name>
PATTERN: <event pattern summary>
TARGETS: <list with retry/DLQ config>
RETRY: <policy summary>
SAFETY: <DLQ, idempotency, circular-dep check>
AUDIT: <CloudTrail + CloudWatch + TestEventPattern>
VERDICT: AUTOMATED | MANUAL_STEP_REQUIRED
GAP: <if MANUAL_STEP_REQUIRED, the specific missing piece>
TEMPLATE: <CLI snippet for rule + targets>
```

## When to invoke

Paste an event source and desired action and ask any of:

- "design an EventBridge workflow for GuardDuty findings"
- "trigger Lambda on S3 object created"
- "build a CodeBuild failure notification"
- "wire Step Functions to Security Hub findings"
- "set up EventBridge Pipes from DynamoDB Streams"
- "configure EventBridge Scheduler for nightly reports"
- "review my existing EventBridge rule"
- "add DLQ to my Lambda target"
- "make my Lambda consumer idempotent"

A bare source + target ("GuardDuty to Lambda", "S3 to SQS") also
routes here via the orchestrator.

## Inputs

- Event source (e.g., `aws.guardduty`, `aws.codebuild`, application
  custom source).
- Event detail-type if known (e.g., `GuardDuty Finding`,
  `CodeBuild Build State Change`).
- Desired target type and ARN.
- Sample event payload (optional, for `TestEventPattern` validation).
- For existing-rule review: rule name + targets + DLQ/retry config.

## Outputs

- One ARCHITECTURE block per workflow with BUS, PATTERN, TARGETS,
  RETRY, SAFETY, AUDIT, VERDICT, and TEMPLATE fields.
- For AUTOMATED verdicts: a working CLI snippet (`put-rule` +
  `put-targets` + `lambda add-permission`).
- For MANUAL_STEP_REQUIRED verdicts: a specific GAP citation
  (missing DLQ, missing idempotency, detected circular dependency,
  missing invocation permission, etc.).
- DLQ + retry policy + idempotency recommendations for every
  workflow.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Automate specialist for App Integration).
- `/aws:audit-eventbridge-bus-policy` for bus-policy ingestion-gate
  audit (companion to this skill's routing-gate focus).
- `/aws:automate-remediation-workflow` when the event-driven
  workflow triggers an SSM Automation remediation.
