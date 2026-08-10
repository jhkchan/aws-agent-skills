---
description: Provision Amazon EventBridge rules and targets (pattern or schedule) with DLQ, retry, input transformation, and cross-account wiring.
nl_triggers:
  - "deploy EventBridge rule"
  - "create EventBridge rule"
  - "EventBridge rule target"
  - "EventBridge scheduled rule"
  - "EventBridge cron rule"
  - "EventBridge rate rule"
  - "event pattern matching"
  - "EventBridge input transformer"
  - "EventBridge DLQ"
  - "retry policy EventBridge"
  - "cross-account event bus"
  - "custom event bus"
  - "EventBridge archive replay"
  - "EventBridge API destination"
  - "EventBridge Scheduler vs rules"
  - "EventBridge Pipes vs rules"
  - "global endpoints EventBridge"
  - "Schema Registry EventBridge"
  - "provision event bus"
routes_to: eventbridge-rule-deployer
---

# /aws:deploy-eventbridge-rule

Activate the `eventbridge-rule-deployer` skill and provision an
EventBridge rule with the correct pattern (or schedule), target
wiring, retry policy, DLQ, input transformer, and cross-account
bus policy.

## What it does

Reads an event source and desired target (or a schedule
requirement plus target), then applies a 12-step deployment
process:

1. Pick pattern vs schedule rule type.
2. Write the event pattern with content-based filtering.
3. Pick target type (Lambda, Step Functions, SQS, SNS, API
   destination, ECS, Systems Manager, Batch, Redshift, SageMaker,
   API Gateway, Kinesis).
4. Wire retry policy and per-target DLQ.
5. Configure input transformation (InputPathsMap, InputTemplate).
6. Deploy cross-account event routing (bus policy + producer
   PutEvents).
7. Use custom event bus vs default bus.
8. Configure archive and replay.
9. Pick between Rules, Pipes, Scheduler.
10. Configure global endpoints (multi-region failover).
11. Enable Schema Registry.
12. Verify the deployment.

Emits a deterministic VERDICT per rule:

```text
PLAN: <reference>
RULE: Name, Bus, Type, Pattern, State
TARGETS: list with retry/DLQ/transform/permission status
RETRY: policy summary
DLQ: arn with retention
INPUT_TRANSFORM: map summary or full event
CROSS_ACCOUNT: bus policy summary or none
PREREQUISITES: 7-item checklist
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
GAP: specific missing item(s) if PREREQUISITES_MISSING
TEMPLATE: CLI snippet for put-rule + put-targets + add-permission
```

## When to invoke

Paste an event source and desired target (or a schedule + target)
and ask any of:

- "deploy an EventBridge rule for GuardDuty findings"
- "trigger Lambda on S3 object created"
- "schedule a Step Functions state machine nightly"
- "wire SQS to Security Hub findings"
- "configure cross-account event routing"
- "set up an EventBridge archive"
- "deploy an API destination"
- "add DLQ to my Lambda target"
- "configure an input transformer"

A bare source + target ("GuardDuty to Lambda", "S3 to SQS") also
routes here via the orchestrator.

## Inputs

- Event source (e.g., `aws.guardduty`, `aws.codebuild`, custom
  application source).
- Event detail-type if known (e.g., `GuardDuty Finding`,
  `CodeBuild Build State Change`).
- Desired target type and ARN.
- Schedule expression (cron/rate) for schedule rules.
- Sample event payload (optional, for `TestEventPattern` validation).
- DLQ ARN if already created; otherwise the skill will include
  creation in the plan.
- Cross-account producer account ID (if applicable).

## Outputs

- One PLAN block per rule with RULE, TARGETS, RETRY, DLQ,
  INPUT_TRANSFORM, CROSS_ACCOUNT, PREREQUISITES, VERDICT, GAP,
  and TEMPLATE fields.
- For READY_TO_DEPLOY verdicts: a working CLI snippet
  (`put-rule` + `put-targets` + `lambda add-permission` + DLQ
  setup).
- For PREREQUISITES_MISSING verdicts: a specific GAP citation
  (missing DLQ, missing invocation permission, missing bus
  policy, idempotency note missing, etc.).
- DLQ + retry policy + idempotency recommendations for every
  rule deployment.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill
  is the Phase 1 Deploy specialist for App Integration).
- `/aws:automate-event-driven-architecture` for end-to-end
  event-driven architecture design (Phase 4 Automate specialist).
- `/aws:audit-eventbridge-bus-policy` for bus-policy ingestion-gate
  audit (companion to this skill's deployment focus).
