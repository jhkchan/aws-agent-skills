# End-to-end usage scenario: sqs-dlq-operator

A walkthrough showing the skill (1) creating a Standard DLQ and wiring
the redrive policy, (2) diagnosing a DLQ filling with valid messages
(false-positive visibility-timeout race), and (3) replaying 1247
messages via StartMessageMoveTask after the root cause is fixed. Each
path includes pre-checks, CONFIRM gate, and post-verification — and is
contrasted with the BLOCKED case where pre-checks catch a problem
before it causes data loss.

## Input (user prompt)

> Create a DLQ for the prod-orders queue. Then figure out why
> prod-orders-dlq has 1247 messages in it — they all look valid to me.
> Then replay them back once the root cause is fixed.

```json
{
  "Source": "prod-orders (Standard)",
  "DLQ": "prod-orders-dlq (new)",
  "Region": "us-east-1",
  "Account": "111111111111"
}
```

## Skill output — create DLQ + redrive (READY)

```text
OPERATION: create
VERDICT: READY
TARGET: prod-orders (source) -> prod-orders-dlq (new DLQ)
PRE_CHECKS:
  - [PASS] Source queue prod-orders exists (Standard, VisibilityTimeout=60)
  - [PASS] DLQ name prod-orders-dlq available
  - [PASS] DLQ type matches source: Standard (FifoQueue=false)
  - [PASS] DLQ retention will be 14 days (1209600s)
  - [PASS] maxReceiveCount=5 >= 3
  - [PASS] VisibilityTimeout 60s >= Lambda p99 of 8s — no race
  - [PASS] Lambda event source mapping has ReportBatchItemFailures enabled
STEPS:
  1. CONFIRM: About to create prod-orders-dlq and wire redrive on prod-orders. This CREATEs a new DLQ (14-day retention, SSE-SQS) and attaches a redrive policy (maxReceiveCount=5). Proceed? (yes/no)
  2. aws sqs create-queue --queue-name prod-orders-dlq --attributes MessageRetentionPeriod=1209600,SqsManagedSseEnabled=true
  3. DLQ_ARN=$(aws sqs get-queue-attributes --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/prod-orders-dlq --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)
  4. aws sqs set-queue-attributes --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/prod-orders --attributes RedrivePolicy='{"deadLetterTargetArn":"'$DLQ_ARN'","maxReceiveCount":"5"}'
POST_VERIFY:
  - (pending execution)
  - get-queue-attributes on prod-orders returns RedrivePolicy with DLQ ARN and maxReceiveCount=5
STATE: pending — DLQ empty until messages exhaust maxReceiveCount on source
NOTES:
  - Type match: Standard DLQ for Standard source. FIFO DLQ would silently drop redriven messages.
  - VisibilityTimeout 60s >= 6x Lambda p99 (8s) — no false-positive race.
  - ReportBatchItemFailures enabled — single failed message retries alone, not the entire batch.
```

## Skill output — analyze DLQ (BLOCKED, false-positive race)

```text
OPERATION: analyze
VERDICT: BLOCKED
TARGET: prod-orders-dlq (depth: 1247)
PRE_CHECKS:
  - [PASS] DLQ prod-orders-dlq exists, ApproximateNumberOfMessagesVisible: 1247
  - [PASS] Received 10 sample messages, all with valid JSON payloads (no poison pills)
  - [PASS] Lambda event source mapping inspected
  - [FAIL] Lambda event source mapping does NOT have ReportBatchItemFailures enabled. A single failed message causes the entire batch of 10 to retry, burning maxReceiveCount on healthy messages.
  - [FAIL] VisibilityTimeout 30s < Lambda p99 Duration 52s. Messages return to the queue before processing completes; receive count increments on every redelivery — the #1 false-positive DLQ cause.
STEPS: (none — pre-checks failed; this is a diagnosis)
POST_VERIFY: (none)
STATE: DLQ depth 1247, all sampled messages have valid payloads (no poison pills)
NOTES:
  - Root cause: configuration race, not poison pill. Two issues:
    1. Enable ReportBatchItemFailures on the Lambda event source mapping.
    2. Increase VisibilityTimeout to >= 312s (6x p99 of 52s) on BOTH the queue AND the event source mapping (mapping overrides queue).
  - After fixing config, replay the 1247 messages via StartMessageMoveTask — they are valid payloads.
  - Remediation:
    aws lambda update-event-source-mapping --uuid a1b2c3d4 --function-response-types ReportBatchItemFailures --visibility-timeout 312
    aws sqs set-queue-attributes --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/prod-orders --attributes VisibilityTimeout=312
    aws sqs start-message-move-task --source-arn arn:aws:sqs:us-east-1:111111111111:prod-orders-dlq --destination-arn arn:aws:sqs:us-east-1:111111111111:prod-orders --max-number-of-messages-per-second 100
```

## Skill output — replay (COMPLETED)

```text
OPERATION: replay
VERDICT: COMPLETED
TARGET: prod-orders-dlq -> prod-orders (replay)
PRE_CHECKS:
  - [PASS] DLQ prod-orders-dlq exists, depth was 1247 messages
  - [PASS] Source prod-orders exists, listed via list-dead-letter-source-queues
  - [PASS] Source has active Lambda consumer (mapping uuid a1b2c3d4, State: Enabled)
  - [PASS] Root cause fixed: VisibilityTimeout increased to 312s, ReportBatchItemFailures enabled, consumer patched (deploy v1.4.2)
  - [PASS] VisibilityTimeout 312s >= Lambda p99 52s — no race
STEPS:
  1. Snapshot: aws cloudwatch get-metric-statistics (DLQ depth before replay: 1247)
  2. aws sqs start-message-move-task --source-arn arn:aws:sqs:us-east-1:111111111111:prod-orders-dlq --destination-arn arn:aws:sqs:us-east-1:111111111111:prod-orders --max-number-of-messages-per-second 100
  3. Poll: aws sqs list-message-move-tasks --source-arn arn:aws:sqs:us-east-1:111111111111:prod-orders-dlq
POST_VERIFY:
  - [PASS] list-message-move-tasks Status: COMPLETED, FilesMoved: 1247, FilesFailed: 0
  - [PASS] DLQ depth returned to 0 (ApproximateNumberOfMessagesVisible: 0)
  - [PASS] Source queue NumberOfMessagesReceived increased by ~1247 over replay window
  - [PASS] Consumer logs show no errors on replayed messages (root-cause fix confirmed)
STATE: DLQ depth 0, source depth normal, replay task COMPLETED
NOTES:
  - Throttled to 100 msg/s (12.5s total) to avoid overwhelming Lambda concurrency.
  - Standard queue — no FIFO dedup concern.
  - Monitor DLQ depth over next 24h — if messages re-accumulate, root cause was not fully fixed.
```

## What the skill caught that a generic assistant misses

1. **Type-match verification.** A generic assistant creates the DLQ and
   wires the redrive without checking Standard-vs-FIFO. The skill
   verifies the `FifoQueue` attribute matches — type mismatch silently
   drops redriven messages.

2. **Visibility-timeout race detection.** A generic assistant sees "DLQ
   filling" and suggests "check the consumer." The skill compares the
   source `VisibilityTimeout` (30s) against the Lambda Duration p99
   (52s), identifies the race, and prescribes the exact fix (>= 312s =
   6x p99 on BOTH the queue and the event source mapping).

3. **Partial-batch gap.** A generic assistant does not check
   `FunctionResponseTypes` on the Lambda event source mapping. The
   skill detects the missing `ReportBatchItemFailures` and explains how
   a single failed message causes the entire batch of 10 to retry,
   burning maxReceiveCount on healthy messages.

4. **No-active-consumer gate before replay.** A generic assistant
   suggests `StartMessageMoveTask` without checking whether the source
   has a consumer. The skill blocks replay when the Lambda mapping is
   `Disabling` — replaying into a source with no consumer just
   re-accumulates messages.

5. **Replay throttle.** A generic assistant omits
   `MaxNumberOfMessagesPerSecond`. The skill defaults to 100 msg/s to
   avoid overwhelming Lambda concurrency — unlimited replay re-triggers
   the original failure mode.

6. **Post-replay verification.** A generic assistant fires the replay
   and moves on. The skill verifies `list-message-move-tasks` shows
   COMPLETED with 0 failures, DLQ depth returned to zero, and the
   source queue received the messages.

7. **Poison-pill vs false-positive triage.** A generic assistant
   assumes DLQ entries are poison pills. The skill inspects the bodies,
   cross-references with consumer logs, and distinguishes genuine
   poison pills (selective delete) from configuration races (fix
   config + bulk replay).

8. **`purge-queue` prohibition.** A generic assistant may suggest
   `purge-queue` for cleanup. The skill explicitly forbids it —
   `purge-queue` deletes ALL messages including healthy in-flight ones
   and cannot be scoped.

## Slash-command invocation

```
/aws:operate-sqs-dlq
```

Or via the orchestrator:

```
/aws:pipeline
You: "create a DLQ for prod-orders"
```

The orchestrator emits
`[Phase: Operate | Skills routed: sqs-dlq-operator]` and hands off to
this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "create DLQ for prod-orders"
# [Phase: Operate | Skills routed: sqs-dlq-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After the DLQ is created and the redrive wired:

```bash
# Verify the redrive policy on the source
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/prod-orders \
  --attribute-names RedrivePolicy \
  --profile default \
  --output json

# Monitor DLQ depth over time
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS --metric-name ApproximateNumberOfMessagesVisible \
  --dimensions Name=QueueName,Value=prod-orders-dlq \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Average Sum \
  --profile default

# List sources feeding this DLQ (cross-account check)
aws sqs list-dead-letter-source-queues \
  --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/prod-orders-dlq \
  --profile default

# After replay, verify task completion
aws sqs list-message-move-tasks \
  --source-arn arn:aws:sqs:us-east-1:111111111111:prod-orders-dlq \
  --profile default \
  --max-results 5
