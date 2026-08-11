---
name: sqs-dlq-operator
description: >-
  Operates SQS dead-letter queue lifecycles safely: creates DLQs with correct type (Standard vs FIFO matching source), tunes redrive policy maxReceiveCount against consumer semantics, analyzes DLQ messages to diagnose why redriven (poison-pill payload, visibility-timeout race, IAM denial, partial-batch gap), replays messages back to source via StartMessageMoveTask (2022+ replacement for deprecated Redrive), monitors DLQ depth via ApproximateNumberOfMessagesVisible + ApproximateAgeOfOldestMessage, and wires the latest surfaces — Lambda partial-batch responses (ReportBatchItemFailures) to prevent false positives, redrive allowlists via RedriveAllowPolicy.
  Enforces safety: type-match check, retention=14 days, CONFIRM gate, snapshot before replay, maxReceiveCount >= 3, idempotent-consumer verification.
  Emits READY with exact CLI + CONFIRM gate, BLOCKED when pre-checks fail, or COMPLETED when replay confirmed and DLQ depth returned to zero.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). No AWS CLI required for offline plan classification.
  Live-account operations use aws sqs create-queue, set-queue-attributes,
  get-queue-attributes, list-queues, list-dead-letter-source-queues,
  start-message-move-task, list-message-move-tasks, receive-message,
  delete-message, purge-queue, aws lambda list-event-source-mappings /
  update-event-source-mapping, aws cloudwatch get-metric-statistics,
  aws logs filter-log-events. Requires AWS CLI v2 with sqs, lambda,
  cloudwatch, and logs access (SSO or key-based).
keywords:
  - SQS
  - dead-letter queue
  - DLQ
  - redrive policy
  - maxReceiveCount
  - StartMessageMoveTask
  - message replay
  - poison pill
  - visibility timeout
  - partial batch response
  - ReportBatchItemFailures
  - ApproximateNumberOfMessagesVisible
  - ApproximateAgeOfOldestMessage
  - RedriveAllowPolicy
  - FIFO DLQ
  - Standard DLQ
  - Lambda event source mapping
  - DLQ analysis
tags: [sqs, messaging, app-integration, dead-letter-queue, dlq, operate, redrive, replay]
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: AppIntegration
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY | BLOCKED | COMPLETED"
  when_to_use: >-
    Creating or tuning an SQS dead-letter queue (Standard or FIFO),
    wiring a redrive policy with the right maxReceiveCount, diagnosing
    why messages landed in the DLQ (poison pill, visibility-timeout
    race, IAM denial, partial-batch gap), replaying messages from DLQ
    back to source via StartMessageMoveTask, monitoring DLQ depth via
    ApproximateNumberOfMessagesVisible, configuring Lambda partial
    batch responses (ReportBatchItemFailures) to prevent false-positive
    DLQ entries, or scoping cross-account redrive via RedriveAllowPolicy.
    Do NOT invoke for greenfield queue provisioning (use
    sqs-queue-deployer) or for DLQ policy security audits (use
    sqs-dlq-policy-auditor).
  activation_triggers:
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
  invocation_schema: >-
    Input: either (a) a DLQ operation intent (create, tune-redrive,
    analyze, replay) with target queue name(s), OR (b) a DLQ URL for
    live-account diagnosis or replay. Output: deterministic
    OPERATION / VERDICT / TARGET / PRE_CHECKS / STEPS / POST_VERIFY /
    STATE / NOTES block where VERDICT is one of READY, BLOCKED,
    COMPLETED.
---

# SQS DLQ Operator

## What this skill does

Executes SQS dead-letter queue operations correctly and safely. Runs
deterministic pre-checks before any state-changing CLI, emits the exact
`create-queue` / `set-queue-attributes` / `start-message-move-task`
sequence behind a CONFIRM gate, and verifies DLQ state after apply. The
skill covers five operations: create (DLQ + redrive wiring), tune
(maxReceiveCount adjustment), analyze (why messages landed in DLQ),
replay (StartMessageMoveTask back to source), and monitor (DLQ depth
metrics + alerting).

Every operation surfaces the type-match trap (Standard DLQ for Standard
queue, FIFO DLQ for FIFO queue — SQS silently drops on mismatch) and
the maxReceiveCount-vs-visibility-timeout race that causes the majority
of false-positive DLQ entries.

## Quick navigation

| # | Section | Jump when |
|---|---|---|
| 1 | [Quick reference](#quick-reference--verdict-thresholds) | Verdict thresholds + pre-check priority |
| 2 | [Pre-flight gate](#pre-flight-dlq-metadata-gate) | Before any CLI — short-circuit broken sources |
| 3 | [Process — operations](#process--operation-planning-apply-in-order) | Per-operation planning: create, tune, analyze, replay |
| 4 | [Common patterns](#common-dlq-patterns-boilerplate) | DLQ creation, redrive wiring, replay boilerplate |
| 5 | [STRICT output contract](#strict-output-contract) | The exact VERDICT block the skill emits |
| 6 | [NEVER anti-patterns](#never-things-to-never-do) | Top taboos |
| 7 | [Expert heuristic](#expert-heuristic-false-positive-dlq-triage) | "Why did this land in the DLQ?" decision tree |
| 8 | [Recent AWS features](#recent-aws-features-2024-2026) | What changed in 24 months |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (DLQ type mismatch, source queue missing, no consumer on source, maxReceiveCount < 3, partial-batch gap detected) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |
| `COMPLETED` | Operation applied and post-verification passed (DLQ depth returned to zero, replay task status RUNNING/COMPLETED, source queue receiving) | Emit post-verify summary |

**Priority order for pre-checks (all must pass for READY):**

1. **DLQ type matches source type** — Standard DLQ for Standard source, FIFO DLQ (`.fifo` suffix) for FIFO source. Mismatch = SQS silently drops redriven messages.
2. **Source queue exists and is active** — `get-queue-url` returns a valid URL.
3. **DLQ retention = 14 days (1209600s)** — default 4 days is too short for weekend/holiday coverage.
4. **maxReceiveCount >= 3** — values of 1 or 2 cause false positives on transient failures.
5. **Consumer (Lambda/EC2/ECS) attached to source** — replaying messages into a source with no consumer just re-accumulates them.
6. **Visibility timeout >= consumer p99 processing time** — if shorter, receive count increments on every redelivery even though the consumer did not fail.
7. **Lambda event source mapping uses ReportBatchItemFailures** (if Lambda) — without it, a single failed message in a batch of 10 causes all 10 to retry, burning maxReceiveCount.

**Detection lag baselines (2026):**
- Message enters DLQ within seconds of the final failed `ReceiveMessage` (after maxReceiveCount attempts).
- `ApproximateNumberOfMessagesVisible` on the DLQ updates within 60s.
- `ApproximateAgeOfOldestMessage` tells you how long the DLQ has been accumulating.

## Mindset

Three SQS DLQ realities drive every operation:

- **The DLQ is a symptom, not a root cause.** Messages land in the DLQ
  because the consumer failed to process them within
  `maxReceiveCount` attempts. Replaying them without fixing the
  consumer just re-accumulates them. Always diagnose the root cause
  before replaying.

- **Type mismatch is the silent killer.** A Standard source with a FIFO
  DLQ (or vice versa) does NOT error at redrive-policy configuration
  time. SQS silently drops the redriven messages — they vanish from
  the source, never appear in the DLQ, and are gone forever. This is
  the #1 DLQ deployment bug.

- **Visibility-timeout race is the #1 false-positive cause.** If
  `VisibilityTimeout` on the source is shorter than the consumer's p99
  processing time, the message returns to the queue before processing
  completes. SQS increments `ApproximateNumberOfReceives` on every
  delivery. After `maxReceiveCount` deliveries, the message redrives —
  even though the consumer never actually failed. The consumer just
  had not finished yet.

## Pre-flight: DLQ metadata gate (run before any operation)

Run before classification. `get-queue-attributes` returns the redrive
policy, DLQ ARN, and source-queue metadata needed to classify the
operation.

**Live-account pre-flight (skip if offline plan):**
1. `aws sqs get-queue-url --queue-name <source>` — confirm source exists.
2. `aws sqs get-queue-attributes --queue-url <source> --attribute-names All` — capture `RedrivePolicy`, `VisibilityTimeout`, `QueueArn`, `FifoQueue`.
3. `aws sqs get-queue-url --queue-name <dlq>` — confirm DLQ exists (if create operation, this is the pre-create check).
4. `aws sqs get-queue-attributes --queue-url <dlq> --attribute-names All` — capture `MessageRetentionPeriod`, `FifoQueue`, `RedriveAllowPolicy`.
5. `aws sqs list-dead-letter-source-queues --queue-url <dlq>` — enumerate sources feeding this DLQ.
6. `aws lambda list-event-source-mappings --event-source-arn <source-arn>` — capture Lambda consumer config (BatchSize, VisibilityTimeout, FunctionResponseTypes).
7. `aws cloudwatch get-metric-statistics --namespace AWS/SQS --metric-name ApproximateNumberOfMessagesVisible --dimensions QueueName=<dlq-name>` — DLQ depth over the last hour.

**Malformed input:** emit `VERDICT: ERROR` with reason and remediation.

| Attribute | Effect on operation |
|---|---|
| `RedrivePolicy` missing on source | Source has no DLQ — create operation needed. |
| `RedrivePolicy.deadLetterTargetArn` points to wrong-type DLQ | Type mismatch — silently drops. Tune must fix. |
| `MessageRetentionPeriod` < 1209600 (14 days) | Messages expire before ops can analyze. Tune to 14 days. |
| `maxReceiveCount` < 3 | False positives on transient failures. Tune to >= 3. |
| `VisibilityTimeout` < consumer p99 | Messages redelivered before consumer finishes — #1 false-positive cause. |
| Lambda mapping without `ReportBatchItemFailures` | Single failed message retries the entire batch — burns maxReceiveCount. |
| `RedriveAllowPolicy` missing on DLQ | Cross-account redrive defaults to deny. Add allowlist for source account. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious SQS DLQ behaviors

- **Type mismatch is SILENT.** A Standard source with a FIFO DLQ (or
  vice versa) does NOT error at redrive-policy set time. SQS silently
  drops the redriven messages. Always verify the DLQ's `FifoQueue`
  attribute matches the source.
- **`maxReceiveCount` counts per ReceiveMessage, not per consumer.**
  With 10 consumers polling, maxReceiveCount of 5 means ~0.5 effective
  retries per consumer. A burst of consumers can exhaust the count
  without any single consumer actually failing.
- **VisibilityTimeout < consumer p99 = false-positive DLQ entries.**
  The message returns to the queue before processing completes; SQS
  re-delivers; receive count increments; eventually redrives. The
  consumer never threw an exception.
- **Lambda event source mapping `VisibilityTimeout` OVERRIDES the queue
  value.** Setting `VisibilityTimeout` on the queue alone is
  insufficient — the Lambda mapping value wins. Check both.
- **Without `ReportBatchItemFailures`, a single failed message retries
  the ENTIRE batch.** If Lambda processes 9 of 10 successfully and 1
  throws, all 10 are returned to the queue. Each receives a new
  receive count. After `maxReceiveCount` cycles, all 10 redrive —
  including the 9 that succeeded (now duplicated).
- **`StartMessageMoveTask` is the 2022+ replacement for the deprecated
  `Redrive` API.** The legacy `Redrive` API is gone; use
  `start-message-move-task`. It is asynchronous, supports filtering via
  `MaxNumberOfMessagesPerSecond`, and is idempotent per task ID.
- **`StartMessageMoveTask` on a FIFO DLQ preserves `MessageGroupId` and
  `MessageDeduplicationId`.** Deduplication applies — if the original
  `MessageDeduplicationId` is within the 5-min window, the redriven
  message is silently dropped.
- **`purge-queue` deletes ALL messages and cannot be scoped.** Never
  use it as remediation for poison-pill messages — it destroys evidence
  and all in-flight messages. Use `receive-message` + `delete-message`
  for selective removal, or `StartMessageMoveTask` for replay.
- **DLQ retention default is 4 days, not 14.** The 4-day default is too
  short for weekend/holiday coverage. Always set to 14 days
  (1209600s) — the maximum.
- **`RedriveAllowPolicy` controls cross-account redrive.** Without it,
  the DLQ defaults to allowing redrive only from the owning account.
  For cross-account source queues, add an allowlist.
- **A DLQ should NOT have its own redrive policy.** That creates an
  infinite redrive chain. The DLQ is terminal.
- **`ApproximateNumberOfMessagesVisible` is approximate.** It lags by
  up to 60s. For exact counts, use `receive-message` with
  `MessageAttributeNames.1=All` and iterate.

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL pre-checks. If ANY fails, verdict is BLOCKED with failures in
PRE_CHECKS. Do NOT execute.

**For ALL operations:**
1. Source queue exists (`get-queue-url` returns a valid URL).
2. DLQ exists (for tune/analyze/replay) or will be created (for create).
3. IAM role holds `sqs:CreateQueue` / `SetQueueAttributes` /
   `StartMessageMoveTask` / `ReceiveMessage` / `DeleteMessage`.

**For create (DLQ + redrive wiring):**
4. DLQ type matches source type (`FifoQueue` attribute identical).
5. DLQ retention = 14 days (1209600s).
6. DLQ name ends in `.fifo` if source is FIFO.
7. Source has no existing redrive policy (or operator confirms overwrite).

**For tune (maxReceiveCount adjustment):**
4. Existing `RedrivePolicy` parses correctly (valid JSON with
   `deadLetterTargetArn` and `maxReceiveCount`).
5. New maxReceiveCount >= 3.
6. `VisibilityTimeout` on source >= consumer p99 (else tuning
   maxReceiveCount is treating the symptom, not the cause).

**For analyze (why messages went to DLQ):**
4. DLQ depth > 0 (`ApproximateNumberOfMessagesVisible` > 0).
5. `receive-message` on DLQ returns at least one message for inspection.
6. Lambda event source mapping inspected for `ReportBatchItemFailures`
   (if Lambda consumer).

**For replay (StartMessageMoveTask):**
4. Source queue exists and is the correct destination (verify via
   `list-dead-letter-source-queues`).
5. Source has an active consumer (Lambda mapping or EC2/ECS worker) —
   otherwise replayed messages just re-accumulate.
6. Root cause of original DLQ entry is fixed (consumer patched,
   visibility timeout increased, poison-pill schema handled) —
   otherwise replayed messages redrive again.
7. `MaxNumberOfMessagesPerSecond` chosen to avoid overwhelming the
   consumer (default: unlimited — dangerous for large DLQs).

### Step 2: READY — emit operation plan

Emit `VERDICT: READY` with exact CLI sequence + CONFIRM gate:
- Exact AWS CLI command with all flags populated.
- Expected effect (DLQ depth change, replay task status transition).
- Expected side-effects (consumer receives replayed messages, dedup
  window may drop FIFO messages).
- CONFIRM gate prompt.

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`create-queue`, `set-queue-attributes`, `start-message-move-task`,
  `delete-message`, `purge-queue`), emit CONFIRM prompt. Do NOT execute
  until confirmed.
- Snapshot current state: `get-queue-attributes --attribute-names All
  --output json > /tmp/<queue>-backup-$(date +%s).json`.
- For replay, capture pre-replay DLQ depth via
  `ApproximateNumberOfMessagesVisible`.
- Execute the CLI.

### Step 4: Post-verification — COMPLETED

ALL checks must pass for `COMPLETED`:
1. For create: `get-queue-attributes` on source returns the new
   `RedrivePolicy` with correct DLQ ARN and maxReceiveCount.
2. For tune: `RedrivePolicy.maxReceiveCount` reflects the new value.
3. For replay: `list-message-move-tasks` shows task status
   `COMPLETED` (or `RUNNING` for large DLQs — partial COMPLETED).
4. For replay: DLQ depth decreasing toward zero; source queue
   `NumberOfMessagesReceived` increasing.
5. For analyze: root cause identified and remediation plan emitted
   (this is a BLOCKED verdict — analysis does not auto-fix).

If ANY verification fails, emit `VERDICT: ERROR` — do not claim COMPLETED.

## Common DLQ patterns (boilerplate)

### Create Standard DLQ + wire redrive policy

```bash
# 1. Create the DLQ (Standard, 14-day retention, SSE-SQS)
aws sqs create-queue \
  --queue-name prod-orders-dlq \
  --attributes MessageRetentionPeriod=1209600,SqsManagedSseEnabled=true

DLQ_URL=$(aws sqs get-queue-url --queue-name prod-orders-dlq --query 'QueueUrl' --output text)
DLQ_ARN=$(aws sqs get-queue-attributes --queue-url "$DLQ_URL" \
  --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)

# 2. Wire the redrive policy on the SOURCE queue
SOURCE_URL=$(aws sqs get-queue-url --queue-name prod-orders --query 'QueueUrl' --output text)
aws sqs set-queue-attributes \
  --queue-url "$SOURCE_URL" \
  --attributes RedrivePolicy="{\"deadLetterTargetArn\":\"$DLQ_ARN\",\"maxReceiveCount\":\"5\"}"
```

### Create FIFO DLQ (for FIFO source)

```bash
# FIFO DLQ — name MUST end in .fifo
aws sqs create-queue \
  --queue-name prod-orders-dlq.fifo \
  --attributes FifoQueue=true,MessageRetentionPeriod=1209600,SqsManagedSseEnabled=true

# Verify the DLQ ARN ends in .fifo before wiring the source
DLQ_ARN=$(aws sqs get-queue-attributes --queue-url "$DLQ_URL" \
  --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)
# DLQ_ARN should be: arn:aws:sqs:us-east-1:111111111111:prod-orders-dlq.fifo
```

### Tune maxReceiveCount

```bash
# Snapshot first
aws sqs get-queue-attributes --queue-url "$SOURCE_URL" \
  --attribute-names RedrivePolicy --output json > /tmp/source-redrive-backup-$(date +%s).json

# Update with new maxReceiveCount (preserving the DLQ ARN)
aws sqs set-queue-attributes \
  --queue-url "$SOURCE_URL" \
  --attributes RedrivePolicy="{\"deadLetterTargetArn\":\"$DLQ_ARN\",\"maxReceiveCount\":\"10\"}"
```

### Analyze DLQ messages (receive without deleting)

```bash
# Receive up to 10 messages from the DLQ for inspection (DO NOT delete yet)
aws sqs receive-message \
  --queue-url "$DLQ_URL" \
  --max-number-of-messages 10 \
  --visibility-timeout 300 \
  --attribute-names All \
  --message-attribute-names All \
  --output json

# Key attributes to inspect:
# - ApproximateReceiveCount: how many times the source redelivered before DLQ
# - ApproximateFirstReceiveTimestamp: when the message first entered the DLQ
# - MessageDeduplicationId (FIFO): for dedup analysis
# - Body: parse for poison-pill indicators (malformed JSON, missing fields)
```

### Replay via StartMessageMoveTask (2022+ API)

```bash
# Pre-replay snapshot of DLQ depth
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS --metric-name ApproximateNumberOfMessagesVisible \
  --dimensions Name=QueueName,Value=prod-orders-dlq \
  --start-time 2026-08-11T00:00:00Z --end-time 2026-08-11T01:00:00Z \
  --period 300 --statistics Average

# Start the move task (asynchronous)
TASK_ID=$(aws sqs start-message-move-task \
  --source-arn "$DLQ_ARN" \
  --destination-arn "$SOURCE_ARN" \
  --max-number-of-messages-per-second 100 \
  --query 'TaskHandle' --output text)

# Poll task status (initial: RUNNING, final: COMPLETED or FAILED)
aws sqs list-message-move-tasks \
  --source-arn "$DLQ_ARN" \
  --max-results 10

# Post-replay: verify DLQ depth returned to zero
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS --metric-name ApproximateNumberOfMessagesVisible \
  --dimensions Name=QueueName,Value=prod-orders-dlq \
  --start-time $(date -u -d '15 min ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Average
```

**`MaxNumberOfMessagesPerSecond`:** set to a value the consumer can
sustain. Default is unlimited — for a DLQ with 100k messages and a
Lambda consumer with 50 concurrent executions, unlimited replay will
throttle the consumer and re-trigger the original failure mode. Start
with `100` (360k/hour) and increase if the consumer keeps up.

### Enable partial batch responses (prevent false-positive DLQ)

```bash
# Update the Lambda event source mapping to report per-message failures
aws lambda update-event-source-mapping \
  --uuid <mapping-uuid> \
  --function-response-types ReportBatchItemFailures

# Verify
aws lambda get-event-source-mapping \
  --uuid <mapping-uuid> \
  --query 'FunctionResponseTypes'
```

Without `ReportBatchItemFailures`, a single failed message in a batch
of 10 causes all 10 to retry. With it, only the failed message retries.

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no
conversational opening:

```text
OPERATION: <create | tune | analyze | replay | monitor>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <source-or-dlq-name>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. CONFIRM: About to <operation> on queue <name> in account <account> region <region>. This will <consequence>. Proceed? (yes/no)
  2. <exact CLI command with every flag populated — no placeholders>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
STATE: <DLQ depth, source depth, replay task status>
NOTES: <type-match rationale, maxReceiveCount rationale, visibility-timeout check, replay throttle>
```

### FORBIDDEN output patterns

- NEVER start with conversational preamble ("Let me analyze…") — the
  VERDICT block is the FIRST line, always. Use uppercase verdict values
  only (`READY`, `BLOCKED`, `COMPLETED`).
- NEVER omit PRE_CHECKS — every pre-check must appear with `[PASS]` or
  `[FAIL]` and a specific reason for each failure.
- NEVER emit a CLI command with placeholder flags in a READY plan —
  every flag must be populated with actual values from the input.
- NEVER claim COMPLETED without every POST_VERIFY line showing `[PASS]`,
  and never omit the CONFIRM gate as the first STEPS entry for
  state-changing operations.
- NEVER recommend `purge-queue` as remediation for poison-pill messages
  — it deletes ALL messages and cannot be scoped.

## NEVER (things to never do)

- NEVER create a Standard DLQ for a FIFO source queue (or vice versa).
  SQS silently drops redriven messages on type mismatch — they vanish
  from the source and never appear in the DLQ. Always verify the
  `FifoQueue` attribute matches.

- NEVER set `maxReceiveCount` to 1 or 2. A single transient failure
  (Lambda throttle, cold start, SDK retry) sends the message
  irretrievably to the DLQ. Minimum: 3 (standard), 5 (FIFO where a
  poison pill blocks the entire message group).

- NEVER replay DLQ messages via `StartMessageMoveTask` without fixing
  the root cause first. If the consumer still fails on the same
  poison-pill payload, replayed messages redrive again — burning compute
  and re-accumulating in the DLQ. Diagnose, fix, then replay.

- NEVER use `aws sqs purge-queue` as remediation for poison-pill
  messages. It deletes ALL messages in the queue (including healthy
  ones in flight) and cannot be scoped. Use `receive-message` +
  `delete-message` for selective removal, or `StartMessageMoveTask`
  for replay after fixing the consumer.

- NEVER recommend the legacy `Redrive` API (deprecated 2022). Use
  `aws sqs start-message-move-task` — it is asynchronous, supports
  throttling via `MaxNumberOfMessagesPerSecond`, and is idempotent per
  task ID.

## Expert heuristic: false-positive DLQ triage

The most common DLQ diagnosis question: "are these messages genuinely
poisoned, or did they land here due to a configuration race?" Apply
the decision tree in order:

```
DLQ depth > 0 (ApproximateNumberOfMessagesVisible > 0)
   |
   ├─ Receive a sample message from the DLQ (receive-message, do NOT delete)
   │
   ├─ Inspect the body:
   │    ├─ Malformed JSON / missing required field ──────────► Poison pill (consumer cannot parse)
   │    ├─ Valid payload but business-rule rejection ────────► Logic poison pill (consumer rejects)
   │    └─ Valid payload, consumer should succeed ───────────► Configuration race — keep diagnosing
   │
   ├─ Check ApproximateReceiveCount on the DLQ message:
   │    ├─ Equals maxReceiveCount exactly ──────────────────► Normal redrive (consumer tried N times)
   │    └─ Less than maxReceiveCount ───────────────────────► Anomalous (possible partial-batch gap or manual move)
   │
   ├─ Check VisibilityTimeout vs consumer p99 processing time:
   │    ├─ VisibilityTimeout < p99 ─────────────────────────► FALSE POSITIVE: message returned before consumer finished;
   │    │                                                      receive count incremented on every redelivery. Fix: increase
   │    │                                                      VisibilityTimeout to >= 6x p99. Replay is safe after fix.
   │    └─ VisibilityTimeout >= p99 ─────────────────────────► Keep diagnosing
   │
   ├─ Check Lambda event source mapping for ReportBatchItemFailures:
   │    ├─ Missing (batch retries as a unit) ───────────────► FALSE POSITIVE: single failed message caused entire batch
   │    │                                                      to retry, burning receive count on healthy messages. Fix:
   │    │                                                      enable FunctionResponseTypes=[ReportBatchItemFailures].
   │    └─ Present ──────────────────────────────────────────► Keep diagnosing
   │
   ├─ Check consumer CloudWatch Logs / Lambda errors around the redrive timestamp:
   │    ├─ Errors present (timeout, exception, IAM denial) ─► Genuine consumer failure. Fix the consumer before replay.
   │    └─ No errors ────────────────────────────────────────► Configuration race confirmed (visibility timeout or partial batch)
   │
   └─ Conclusion:
        ├─ Poison pill ──────► Selective delete (receive + delete) OR fix consumer to handle gracefully
        ├─ Config race ──────► Fix config, then replay via StartMessageMoveTask
        └─ Consumer failure ─► Patch consumer, then replay
```

**Per-metric root-cause table:**

| Symptom | Likely root cause | Verification |
|---|---|---|
| DLQ filling, consumer logs show no errors | VisibilityTimeout < p99 (false positive) | Compare Lambda Duration p99 to source VisibilityTimeout |
| DLQ filling, batch of 10 all redriven together | Missing ReportBatchItemFailures | Check event source mapping FunctionResponseTypes |
| DLQ filling, consumer throws on a specific payload | Poison pill (malformed data) | Receive DLQ message, parse body, reproduce in consumer |
| DLQ filling, consumer shows IAM denial | IAM policy gap on consumer role | CloudTrail: AccessDenied around the redrive timestamp |
| DLQ filling, only one MessageGroupId affected (FIFO) | Head-of-line block on a poison-pill group | Receive DLQ messages, group by MessageGroupId |
| DLQ filling after a deploy | Consumer regression (new code throws) | Correlate DLQ spike timestamp with CodeDeploy deployment |

## Pre-flight safety checks (run before any deploy)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`create-queue`, `set-queue-attributes`, `start-message-move-task`,
  `delete-message`, `purge-queue`), emit `CONFIRM:` and wait for `yes`.
- **Snapshot before modification.** `get-queue-attributes --attribute-names
  All --output json > /tmp/<queue>-backup-$(date +%s).json`. The
  redrive policy has no version history and no rollback.
- **Verify type match before wiring redrive.** A Standard source with a
  FIFO DLQ silently drops. Always check the DLQ's `FifoQueue` attribute.
- **Pre-replay DLQ depth snapshot.** Capture
  `ApproximateNumberOfMessagesVisible` before `StartMessageMoveTask` to
  measure replay progress.
- **Verify consumer is healthy before replay.** If the source queue's
  consumer is throwing errors, replayed messages redrive again. Check
  consumer logs first.
- **Throttle replay for large DLQs.** Set
  `MaxNumberOfMessagesPerSecond` to a value the consumer can sustain.
  Default (unlimited) throttles the consumer and re-triggers the
  original failure mode.

## Edge-case handling

- **FIFO DLQ replay drops messages silently.** `StartMessageMoveTask`
  preserves the original `MessageDeduplicationId`. If the original ID
  is within the 5-min dedup window on the source, the redriven message
  is silently dropped. Detect by comparing DLQ depth before replay vs
  source depth after — if source does not increase, dedup is the cause.
- **Cross-account DLQ redrive.** The DLQ's `RedriveAllowPolicy` must
  allowlist the source account. Without it, `StartMessageMoveTask`
  from a cross-account source returns `AccessDenied`. Set:
  `RedriveAllowPolicy={"redrivePermission":"allowList","sourceQueueArns":["arn:aws:sqs:us-east-1:222222222222:source"]}`.
- **DLQ has its own DLQ (infinite chain).** A redrive policy on the DLQ
  pointing to another DLQ creates an infinite chain. The DLQ should be
  terminal — no redrive policy on the DLQ itself.
- **`purge-queue` during replay.** If an operator runs `purge-queue` on
  the DLQ while a `StartMessageMoveTask` is RUNNING, the task fails
  with `PurgeQueueInProgress`. Wait 60s after purge before retrying.
- **Lambda event source mapping `VisibilityTimeout` overrides queue.**
  Setting `VisibilityTimeout` on the queue alone does not fix the race
  if a Lambda mapping exists — the mapping value wins. Update both.
- **DLQ depth metric lag.** `ApproximateNumberOfMessagesVisible` lags
  by up to 60s. For real-time monitoring, use CloudWatch alarm with
  period 60s and DatapointsToAlarm 2 to avoid flapping on lag spikes.

## Recent AWS features (2024-2026)

- **StartMessageMoveTask (2022+, GA 2024-2026):** The current API for
  redriving from DLQ back to source. Replaced the deprecated legacy
  `Redrive` API. Asynchronous, supports `MaxNumberOfMessagesPerSecond`
  throttling, idempotent per task handle. Use this for ALL replay
  operations.
- **SQS partial batch responses (Lambda):** `ReportBatchItemFailures`
  on the event source mapping lets Lambda report which messages in a
  batch failed, so only those are retried. Without it, the entire batch
  retries — the #1 cause of false-positive DLQ entries for Lambda
  consumers.
- **RedriveAllowPolicy (cross-account redrive):** Controls which source
  accounts can redrive to a DLQ. Default: only the DLQ's owning account.
  Set to `allowList` for cross-account source queues.
- **Message retention max 14 days:** More prominently used for DLQs
  (4-day default is too short for weekend/holiday coverage).
- **SSE-SQS (SqsManagedSseEnabled):** Free, FIPS-validated AES-256-GCM.
  Recommended default for DLQs (no key policy to manage).
- **No-SQL payload in message attributes:** Structured attributes for
  filtering without parsing the body — useful for DLQ analysis (tag
  poison-pill messages with an attribute for selective replay).
- **ApproximateNumberOfMessagesVisible CloudWatch metric:** The primary
  DLQ-depth signal. Alarm at threshold > 0 for immediate detection, or
  > N for batch-oriented analysis windows.

## Output format (per operation)

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

### Worked example — create DLQ + redrive (READY)

```text
OPERATION: create
VERDICT: READY
TARGET: prod-orders (source) -> prod-orders-dlq (new DLQ)
PRE_CHECKS:
  - [PASS] Source queue prod-orders exists (Standard, VisibilityTimeout=60)
  - [PASS] DLQ name prod-orders-dlq available (no existing queue)
  - [PASS] DLQ type matches source: Standard (source FifoQueue=false)
  - [PASS] DLQ retention will be set to 14 days (1209600s)
  - [PASS] maxReceiveCount=5 >= 3 (within safe range for Standard queue)
  - [PASS] VisibilityTimeout 60s >= consumer (Lambda) p99 of 8s — no race
  - [PASS] Lambda event source mapping has ReportBatchItemFailures enabled
STEPS:
  1. CONFIRM: About to create prod-orders-dlq and wire redrive on prod-orders in account 111111111111 region us-east-1. This will CREATE a new DLQ (14-day retention, SSE-SQS) and attach a redrive policy (maxReceiveCount=5). Proceed? (yes/no)
  2. aws sqs create-queue --queue-name prod-orders-dlq --attributes MessageRetentionPeriod=1209600,SqsManagedSseEnabled=true
  3. DLQ_ARN=$(aws sqs get-queue-attributes --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/prod-orders-dlq --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)
  4. aws sqs set-queue-attributes --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/prod-orders --attributes RedrivePolicy='{"deadLetterTargetArn":"'$DLQ_ARN'","maxReceiveCount":"5"}'
POST_VERIFY:
  - (pending execution)
  - get-queue-attributes on prod-orders returns RedrivePolicy with DLQ ARN and maxReceiveCount=5
  - DLQ exists with MessageRetentionPeriod=1209600
STATE: pending — DLQ empty until messages exhaust maxReceiveCount on source
NOTES:
  - Type match: Standard DLQ for Standard source. FIFO DLQ would silently drop redriven messages.
  - maxReceiveCount=5 tolerates transient failures (Lambda throttle, cold start, SDK retry). Set to 3 for idempotent consumers that fail fast on real errors.
  - VisibilityTimeout 60s >= 6x Lambda p99 (8s) — no false-positive race.
  - ReportBatchItemFailures enabled — single failed message retries alone, not the entire batch.
```

### Worked example — replay via StartMessageMoveTask (COMPLETED)

```text
OPERATION: replay
VERDICT: COMPLETED
TARGET: prod-orders-dlq -> prod-orders (replay)
PRE_CHECKS:
  - [PASS] DLQ prod-orders-dlq exists, depth was 1247 messages
  - [PASS] Source prod-orders exists, listed via list-dead-letter-source-queues
  - [PASS] Source has active Lambda consumer (mapping uuid a1b2c3d4, BatchSize=10)
  - [PASS] Root cause fixed: consumer patched to handle malformed-JSON payload gracefully (deploy v1.4.2)
  - [PASS] VisibilityTimeout 60s >= Lambda p99 8s — no race
  - [PASS] ReportBatchItemFailures enabled on mapping
STEPS:
  1. Snapshot: aws cloudwatch get-metric-statistics (DLQ depth before replay: 1247)
  2. aws sqs start-message-move-task --source-arn arn:aws:sqs:us-east-1:111111111111:prod-orders-dlq --destination-arn arn:aws:sqs:us-east-1:111111111111:prod-orders --max-number-of-messages-per-second 100
  3. Poll: aws sqs list-message-move-tasks --source-arn arn:aws:sqs:us-east-1:111111111111:prod-orders-dlq
POST_VERIFY:
  - [PASS] list-message-move-tasks Status: COMPLETED, FilesMoved: 1247, FilesFailed: 0
  - [PASS] DLQ depth returned to 0 (ApproximateNumberOfMessagesVisible: 0)
  - [PASS] Source queue NumberOfMessagesReceived increased by ~1247 over replay window
  - [PASS] Consumer logs show no errors on replayed messages (patch confirmed working)
STATE: DLQ depth 0, source depth normal, replay task COMPLETED
NOTES:
  - Throttled to 100 msg/s (12.5s total) to avoid overwhelming Lambda concurrency.
  - FIFO dedup did not apply (Standard queue, no MessageDeduplicationId).
  - Monitor DLQ depth over next 24h — if messages re-accumulate, root cause was not fully fixed.
```

## Domain

AWS CloudOps / App Integration — SQS Dead-Letter Queue Operations.

## AWS documentation

- **Amazon SQS Developer Guide** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/welcome.html
- **SQS Dead-Letter Queues** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html
- **SQS Message Lifecycle** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-message-lifecycle.html
- **SQS RedrivePolicy** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/APIReference/API_SetQueueAttributes.html
- **SQS StartMessageMoveTask** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/APIReference/API_StartMessageMoveTask.html
- **SQS CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/sqs/
- **Lambda Event Source Mapping (SQS)** — https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html
- **SQS Partial Batch Responses** — https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html#services-sqs-batchfailurereporting
- **SQS Visibility Timeout** — https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html
