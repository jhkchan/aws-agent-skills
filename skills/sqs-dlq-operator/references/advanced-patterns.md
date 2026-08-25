# Advanced patterns - SQS DLQ Operator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

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

