---
description: Operate SQS dead-letter queue lifecycles — create DLQ, tune maxReceiveCount, analyze why messages went to DLQ, replay via StartMessageMoveTask, monitor DLQ depth, enable partial batch responses.
nl_triggers:
  - "create SQS DLQ"
  - "dead-letter queue"
  - "tune maxReceiveCount"
  - "redrive policy"
  - "messages stuck in DLQ"
  - "replay DLQ messages"
  - "StartMessageMoveTask"
  - "poison pill message"
  - "DLQ analysis"
  - "why messages went to DLQ"
  - "DLQ depth alarm"
  - "ApproximateNumberOfMessagesVisible"
  - "partial batch response"
  - "ReportBatchItemFailures"
  - "RedriveAllowPolicy"
  - "DLQ redrive"
  - "SQS DLQ"
routes_to: sqs-dlq-operator
---

# /aws:operate-sqs-dlq

Activate the `sqs-dlq-operator` skill and plan/execute an SQS
dead-letter queue operation with deterministic pre-checks, CONFIRM
gate, and post-verification.

## What it does

Reads a DLQ operation intent and applies the priority-ordered
pre-check sequence:

1. Pre-flight DLQ metadata gate — short-circuit cases where the source
   queue is missing, the DLQ type mismatches, or there is no active
   consumer.
2. Pre-check gate — BLOCKED if any check fails (DLQ type mismatch,
   maxReceiveCount < 3, visibility timeout < consumer p99, Lambda
   mapping without ReportBatchItemFailures, no active consumer before
   replay, root cause not fixed before replay).
3. READY — emit the exact CLI sequence with all flags populated
   (create-queue, set-queue-attributes for redrive, start-message-move-
   task for replay, update-event-source-mapping for partial batch), the
   expected effect, and the CONFIRM gate prompt.
4. Execute behind CONFIRM gate — snapshot queue attributes first
   (redrive policy has no version history), execute the CLI, poll
   task status for replay operations.
5. Post-verification — redrive policy reflects the new maxReceiveCount,
   DLQ depth returned to zero, source queue receiving, replay task
   COMPLETED. COMPLETED only if ALL post-verification checks pass.

Emits a deterministic VERDICT per operation:

```text
OPERATION: <create | tune | analyze | replay | monitor>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <source-or-dlq-name>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait or poll command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
STATE: <DLQ depth, source depth, replay task status>
NOTES: <type-match rationale, maxReceiveCount rationale, visibility-timeout check>
```

## When to invoke

Paste a DLQ operation intent or describe the scenario:

- "create a DLQ for the prod-orders queue"
- "tune maxReceiveCount from 3 to 10"
- "why is prod-orders-dlq filling up"
- "replay 1247 messages from the DLQ back to source"
- "enable partial batch responses on the Lambda mapping"
- "set up a DLQ depth alarm"

A bare queue name + any DLQ verb ("fix this DLQ", "drain the DLQ") also
routes here via the orchestrator.

## Inputs

- Source queue name (existing or new).
- DLQ name (for create) or existing DLQ URL (for tune/analyze/replay).
- DLQ type: Standard or FIFO (must match source).
- maxReceiveCount (for create/tune).
- For replay: confirmation that the root cause is fixed and the
  consumer is active.
- For analyze: DLQ URL + consumer (Lambda/EC2/ECS) details.

## Outputs

- One VERDICT block per operation.
- PRE_CHECKS list with `[PASS]` / `[FAIL]` per check and reason for
  failure.
- For READY: the exact CLI sequence, expected effect, and the CONFIRM
  gate prompt.
- For COMPLETED: POST_VERIFY list with `[PASS]` per check, the new DLQ
  depth, replay task status, and follow-up monitoring recommendations.
- For BLOCKED: the specific failure reason and the remediation step
  (e.g., fix the DLQ type, increase visibility timeout, enable
  ReportBatchItemFailures, re-enable the consumer before replay).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Operate specialist for SQS DLQ lifecycle).
- `/aws:deploy-sqs-queue` for greenfield queue provisioning (this skill
  operates the DLQ layer on top of existing queues).
- `/aws:audit-sqs-dlq-policy` for the security-audit side — the auditor
  finds mis-scoped DLQ policies; this operator creates, tunes, analyzes,
  and replays.
