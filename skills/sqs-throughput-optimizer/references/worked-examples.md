# SQS Throughput Optimizer — Worked Examples

Full worked examples for each optimization pattern, including the
long-polling enablement, batch API migration, FIFO high-throughput mode,
visibility timeout rightsizing, already-optimal queue, NEED_MORE_INFO,
and an end-to-end walkthrough.

## Example 1: Long polling enablement (FURTHER_OPTIMIZATION_AVAILABLE)

```text
TARGET: q-long-polling-enablement
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Standard queue with ReceiveMessageWaitTimeSeconds=0 generating
  85M empty receives/month (85% of total ReceiveMessage calls, confirmed
  by CloudWatch NumberOfEmptyReceives). Enabling long polling
  (WaitTimeSeconds=20) projects a 90% reduction in empty receives.
RECOMMENDATION:
  Current: short polling (WaitTimeSeconds=0), 4 EC2 poller threads, VisibilityTimeout=30s, Standard
  Proposed: long polling (WaitTimeSeconds=20), 4 EC2 poller threads, VisibilityTimeout=30s, Standard
  Dimensions changed: polling (Step 1)
  Dimensions checked: polling → (enable long)  batching ✓ (EC2, not ESM — verify code)
    visibility ✓ (30s > poller p95 <1s)  retention ✓ (4 days, healthy)
    redrive ✓ (maxReceiveCount=3, DLQ depth not reported as growing)
    queue-type ✓ (Standard, no ordering needed)  fifo-mode ✓ (N/A)
  Confidence: HIGH — CloudWatch NumberOfEmptyReceives directly measured
    at 85% empty ratio; long polling is a queue attribute change with no
    consumer code modification required.
ESTIMATED_SAVINGS:
  Current monthly: $40.00
    requests: 100M / 1M × $0.40 = $40.00
  Projected monthly: $9.40
    requests: 23.5M / 1M × $0.40 = $9.40
      (8.5M empty @ 90% reduction + 15M non-empty receives)
  Monthly saving: $30.60
    ($40.00 − $9.40 = $30.60 ✓)
  Annual saving: $367.20
MIGRATION_STEPS:
  1. Enable long polling on the queue:
     aws sqs set-queue-attributes --queue-url <url> --attributes ReceiveMessageWaitTimeSeconds=20
  2. Reduce poller thread count from 4 to 2 (long polling replaces tight-loop polling):
     Update EC2 user data / ECS task definition.
  3. Monitor NumberOfEmptyReceives for 7 days post-change:
     aws cloudwatch get-metric-statistics --namespace AWS/SQS --metric-name NumberOfEmptyReceives ...
  4. Verify ApproximateAgeOfOldestMessage stays under 30s.
CONFIRM: About to set-queue-attributes on q-long-polling-enablement
  (WaitTimeSeconds 0 → 20). Monthly saving $30.60 (76.5% request
  reduction). Proceed? (yes/no)
```

## Example 2: FIFO high-throughput mode (FURTHER_OPTIMIZATION_AVAILABLE)

```text
TARGET: q-fifo-high-throughput-mode.fifo
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: FIFO queue at the default 300 TX/s queue-level ceiling (ThroughputLimit
  not configured). Workload sends 500 TX/s across 50 MessageGroupIds.
  ApproximateNumberOfMessagesVisible is 50,000 and rising, indicating the
  queue cannot drain at the current limit. Workload does NOT need
  cross-group deduplication — enabling high-throughput mode raises per-
  group batch throughput to 9,000 TX/s.
RECOMMENDATION:
  Current: FIFO default mode (queue-level 300 TX/s), ContentBasedDeduplication=true, VisibilityTimeout=60s
  Proposed: FIFO high-throughput mode (DeduplicationScope=MessageGroup, ThroughputLimit=PerMessageGroupId), VisibilityTimeout=60s
  Dimensions changed: fifo-mode (Step 6)
  Dimensions checked: polling ✓ (WaitTimeSeconds=20 already)  batching ✓ (ESM BatchSize=10)
    visibility ✓ (60s > Lambda p95)  retention ✓ (4 days)  redrive ✓ (maxReceiveCount=5)
    queue-type ✓ (FIFO, ordering required)  fifo-mode → (enable high-throughput)
  Confidence: HIGH — CloudWatch shows backlog growing at 50K visible msgs;
    50 MessageGroupIds provide ample partitioning; workload confirmed
    independent per-group (no cross-group dedup needed).
ESTIMATED_SAVINGS:
  Current monthly: $516.00
    requests: 1,296M / 1M × $0.40 = $518.40 (minus free tier)
  Projected monthly: $516.00
    requests: same volume (no request reduction — throughput improvement only)
  Monthly saving: $0.00
  Note: This is a THROUGHPUT optimization, not a cost reduction. The queue
  backs up at the current ceiling; enabling high-throughput mode allows the
  queue to drain. No dollar saving, but eliminates backlog-driven SLA risk.
  Verdict is FURTHER_OPTIMIZATION_AVAILABLE because throughput is below
  demand and the backlog is actively growing.
CONFIRM: About to set-queue-attributes on q-fifo-high-throughput-mode.fifo
  (enable DeduplicationScope=MessageGroup, ThroughputLimit=PerMessageGroupId).
  Throughput improvement 300→9000 TX/s batch per MessageGroupId. No cost
  change. Proceed? (yes/no)
```

## Example 3: Already-optimal queue (OPTIMIZED)

```text
TARGET: q-already-optimized-queue
VERDICT: OPTIMIZED
REASON: Standard queue with all seven dimensions at healthy configuration:
  long polling enabled (WaitTimeSeconds=20), batch APIs in use
  (SendMessageBatch for producer, ESM auto-delete for consumer), visibility
  timeout right-sized (120s >> 1.2s p95), empty receive ratio 0.5%,
  DLQ depth 12 messages. No dimension has a savings-bearing recommendation.
RECOMMENDATION:
  Current: long polling (WaitTimeSeconds=20), batch send + ESM auto-delete, VisibilityTimeout=120s, Standard
  Proposed: no change
  Dimensions checked: polling ✓  batching ✓  visibility ✓  retention ✓  redrive ✓  queue-type ✓  fifo-mode ✓ (N/A)
  Confidence: HIGH — all metrics within healthy ranges over 30-day window.
ESTIMATED_SAVINGS:
  Current monthly: $8.84
  Projected monthly: $8.84
  Monthly saving: $0.00
  Annual saving: $0.00
MIGRATION_STEPS:
  1. No action required. Continue monitoring.
CONFIRM: N/A — no state-changing operation.
```

## Example 4: NEED_MORE_INFO (insufficient data)

```text
TARGET: q-new-queue
VERDICT: NEED_MORE_INFO
REASON: Queue was created 3 days ago. CloudWatch metrics window is < 14 days
  minimum. NumberOfEmptyReceives has not yet accumulated enough data to
  assess polling efficiency. Re-evaluate after 14 days of observation.
RECOMMENDATION:
  Current: insufficient data
  Proposed: re-evaluate after 14-day observation window
  Dimensions checked: (not evaluated — data gate failed)
  Confidence: LOW — insufficient observation period.
ESTIMATED_SAVINGS:
  Current monthly: unknown
  Projected monthly: unknown
  Monthly saving: unknown
MIGRATION_STEPS:
  1. Wait 14 days, then re-run optimization analysis.
  2. Ensure CloudWatch detailed monitoring is enabled for the queue.
CONFIRM: N/A — no state-changing operation.
```

## End-to-end walkthrough: multi-dimension optimization

A queue with both empty-receive waste AND single-message delete calls:

```
Queue: notification-dispatch-q (Standard)
  WaitTimeSeconds: 0 (short polling)
  Consumer: ECS Fargate, DeleteMessage one-at-a-time
  10M msgs/month, 50M empty receives/month

Step 1 (polling): empty ratio = 50M / (50M + 10M) = 83% → enable long polling
Step 2 (batching): consumer uses DeleteMessage → switch to DeleteMessageBatch

Combined savings:
  Current: 60M requests × $0.40/M = $24.00/month
  Projected: 12M requests × $0.40/M = $4.80/month
  Monthly saving: $19.20 (80% reduction)
```

Both dimensions stack because they address different request sources
(empty receives vs delete calls). Apply both in the same MIGRATION_STEPS.

## Error handling and edge cases

### CLI / data-source failure handling

| Failure | Cause | Recovery |
|---|---|---|
| `get-queue-attributes` returns `QueueDoesNotExist` | Queue URL stale or deleted | BLOCKED; verify via `list-queues` |
| CloudWatch returns empty | No traffic or wrong QueueName dimension | Check spelling; if dormant, emit OPTIMIZED |
| `list-event-source-mapping` empty | No Lambda ESM for this queue | Note EC2/ECS consumer in recommendation |
| RedrivePolicy JSON parse error | Malformed policy attribute | Use `jq`; BLOCKED if unparseable |

### FIFO cross-group deduplication breakage

When enabling high-throughput mode (`DeduplicationScope=MessageGroup`),
deduplication is scoped to the MessageGroupId only. Two messages with
the same content but different MessageGroupIds will BOTH be accepted.
Verify the workload is truly group-independent before enabling.

### Lambda ESM overrides queue visibility timeout

The ESM's `VisibilityTimeout` overrides the queue attribute. Changing
the queue alone has no effect on Lambda consumers. Always update via:
```bash
aws lambda update-event-source-mapping --uuid <uuid> --visibility-timeout <seconds>
```

### DLQ redrive edge cases

- `StartMessageMoveTask` can redrive to a DIFFERENT queue than source.
- FIFO DLQ and Standard source are incompatible types for redrive.
- maxReceiveCount = 3 for most workloads; 5 for transient-failure-prone
  consumers. Too low causes premature DLQ routing; too high wastes
  retries on poison-pill messages.

### Stuck DLQ (messages not draining)

1. Check if `StartMessageMoveTask` is already running.
2. Fix the consumer BEFORE starting redrive.
3. Use `--max-number-of-messages-per-second` to throttle if needed.

### Backlog growing after optimization

If `ApproximateNumberOfMessagesVisible` keeps rising post-change:
1. The consumer is the bottleneck, not SQS throughput.
2. Increase consumer concurrency (more Lambda executions, more ECS tasks).
3. Do NOT increase polling frequency — this adds empty receives without
   increasing throughput.

### Extended NEVER list

6. NEVER enable long polling on a Lambda ESM consumer — ESM already uses
   long polling internally.
7. NEVER recommend reducing MessageRetentionPeriod as a cost optimization —
   it permanently drops messages, not reduces API cost.
8. NEVER use `aws sqs redrive-allow-policy` as a redrive mechanism — it
   configures permissions, not message movement. Use
   `StartMessageMoveTask`.
9. NEVER change a FIFO queue's DeduplicationScope without verifying
   cross-group dedup is not required.
10. NEVER assume NumberOfMessagesReceived equals individual API calls. If
    `MaxNumberOfMessages > 1`, one call returns multiple messages.

### Worked math — Step 1 polling (empty-receive math)

**The empty-receive math:**
```
empty_receive_ratio =
  NumberOfEmptyReceives / (NumberOfEmptyReceives + NumberOfMessagesReceived)

monthly_wasted_cost =
  NumberOfEmptyReceives / 1,000,000 × $0.40

Example: 85M empty receives/month × $0.40/M = $34/month wasted
         After long polling: empty receives drop 90% → $3.40/month
         Monthly saving: $30.60
```

### Worked math — Step 2 batching (batch savings math)

**Batch savings math:**
```
Single-API request count: N messages × 3 calls (send + receive + delete)
Batch-API request count:  N/10 batches × 3 calls = N × 0.3 calls
Reduction: 10x fewer requests for send and delete, receive is already
batched by SQS (max 10 per ReceiveMessage call).
```

### Worked math — Step 3 visibility (re-delivery cost inflation)

**Re-delivery cost inflation:**
```
re_delivery_rate = re_delivered_messages / total_received
effective_receive_cost = base_receive_cost × (1 + re_delivery_rate)

Example: 15M received + 3M re-delivered (20% re-delivery rate)
  Effective receive cost: 18M × $0.40/M = $7.20/month
  After fixing visibility timeout: 15M × $0.40/M = $6.00/month
  Monthly saving: $1.20/month (plus downstream processing savings)
```

### Worked math — Step 7 impact estimation formulas

```
current_monthly_cost =
  (current_total_api_requests / 1,000,000) × $0.40
  [+ KMS cost if SSE-KMS enabled]

projected_monthly_cost =
  (projected_total_api_requests / 1,000,000) × $0.40
  [+ KMS cost at projected request rate]

monthly_saving = current_monthly_cost - projected_monthly_cost
```

### Output format template (with CONFIRM gate wording)

```text
TARGET: <queue-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <polling strategy>, <batch pattern>, <visibility timeout>, <queue type/mode>
  Proposed: <polling strategy>, <batch pattern>, <visibility timeout>, <queue type/mode>
  Dimensions changed: <polling | batching | visibility | retention | redrive | queue-type>
  Dimensions checked: <list ALL seven, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Current monthly: $<amount>    ← MUST show request breakdown
  Projected monthly: $<amount>
  Monthly saving: $<amount>     ← MUST equal Current − Projected, 2 decimals
  Annual saving: $<amount>      ← MUST equal Monthly × 12
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <queue-name> in <region>.
  Proceed? (yes/no)"
```

### Worked example — Standard queue optimized to long-polling + batch (before/after table)

```text
TARGET: order-events-queue
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Standard queue with ReceiveMessageWaitTimeSeconds=0 generating
  85M empty receives/month (85% of total ReceiveMessage calls).
  Consumer uses DeleteMessage one-at-a-time. Enabling long polling
  (WaitTimeSeconds=20) + DeleteMessageBatch reduces total API requests
  by 74%.

BEFORE/AFTER CONFIG COMPARISON:
  ┌─────────────────────────────┬──────────────────────────┬──────────────────────────────┐
  │ Dimension                   │ CURRENT                  │ RECOMMENDED                  │
  ├─────────────────────────────┼──────────────────────────┼──────────────────────────────┤
  │ Queue type                  │ Standard                 │ Standard (unchanged)         │
  │ Polling mode                │ Short (WaitTimeSeconds=0)│ Long (WaitTimeSeconds=20)    │
  │ Consumer batch size         │ 1 (single-message API)   │ 10 (DeleteMessageBatch)      │
  │ Visibility timeout          │ 30s                      │ 30s (consumer p95=200ms ✓)   │
  │ Message retention           │ 4 days (345600s)         │ 4 days (unchanged)           │
  │ DLQ redrive                 │ maxReceiveCount=3, ok    │ unchanged                    │
  │ FIFO mode                   │ N/A (Standard)           │ N/A (Standard)               │
  └─────────────────────────────┴──────────────────────────┴──────────────────────────────┘

RECOMMENDATION:
  Current: short polling (WaitTimeSeconds=0), single-message delete,
           VisibilityTimeout=30s, Standard
  Proposed: long polling (WaitTimeSeconds=20), batch delete (size 10),
            VisibilityTimeout=30s, Standard
  Dimensions changed: polling (Step 1) + batching (Step 2)
  Dimensions checked: polling → (enable long)  batching → (batch delete)
    visibility ✓ (30s > consumer p95 200ms)  retention ✓ (4 days, healthy)
    redrive ✓ (maxReceiveCount=3, DLQ depth < 50)  queue-type ✓ (Standard)
    fifo-mode ✓ (N/A — Standard queue)
  Confidence: HIGH — CloudWatch NumberOfEmptyReceives directly measured;
    batch delete is a code-level change with no infrastructure risk.

ESTIMATED_SAVINGS:
  Current monthly: $40.00
    Request breakdown: 100M total API requests / 1M × $0.40 = $40.00
      (15M SendMessage + 85M ReceiveMessage [85% empty] +
       15M DeleteMessage one-at-a-time ≈ 15M send + 100M receive + 15M delete)
  Projected monthly: $10.40
    Request breakdown: 26M total API requests / 1M × $0.40 = $10.40
      (15M SendMessage + 8.5M ReceiveMessage [90% empty reduction] +
       1.5M DeleteMessageBatch [10 messages per call])
  Monthly saving: $29.60   ($40.00 − $10.40 = $29.60 ✓)
  Annual saving: $355.20   ($29.60 × 12 = $355.20 ✓)

MIGRATION_STEPS:
  1. Enable long polling on the queue:
     aws sqs set-queue-attributes \
       --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/order-events-queue \
       --attributes ReceiveMessageWaitTimeSeconds=20
  2. Update consumer to use DeleteMessageBatch (replace per-message DeleteMessage):
     aws sqs delete-message-batch \
       --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/order-events-queue \
       --entries file://delete-batch.json
  3. Monitor NumberOfEmptyReceives for 7 days post-change (expect 90% drop):
     aws cloudwatch get-metric-statistics --namespace AWS/SQS \
       --metric-name NumberOfEmptyReceives \
       --dimensions Name=QueueName,Value=order-events-queue \
       --start-time 2026-08-05T00:00:00Z --end-time 2026-08-12T00:00:00Z \
       --period 86400 --statistics Sum
  4. Verify ApproximateAgeOfOldestMessage stays under 60s (no consumer backlog).

CONFIRM: About to set-queue-attributes on order-events-queue
  (WaitTimeSeconds 0 → 20) and switch consumer to batch delete. Monthly
  saving $29.60 (74% request reduction). Proceed? (yes/no)
```
