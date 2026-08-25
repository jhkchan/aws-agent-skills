# Advanced patterns - SQS DLQ Policy Auditor

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Step 0: Expert knowledge — non-obvious SQS behaviours that change classification

These behaviours are easy to misjudge without operational SQS experience.
Each changes a verdict if ignored:

- **`Principal: "*"` in an SQS queue policy is COMMON and usually SAFE.** The
  standard S3-event-notification and SNS-subscription patterns use
  `Principal: "*" + Condition: aws:SourceArn` (or `aws:SourceAccount`). The
  condition restricts access to the specific S3 bucket or SNS topic — it is
  real access control. Do NOT flag these as PUBLIC_ACCESS. Only flag
  `Principal: "*"` with NO strong condition (Step 1).

- **`maxReceiveCount` counts per message delivery, not per consumer.** Every
  `ReceiveMessage` call that delivers a message increments the counter —
  regardless of which consumer received it. With 10 consumers polling, a
  `maxReceiveCount` of 5 means roughly 0.5 effective retries per consumer
  before the message hits the DLQ. High-consumer queues need a HIGHER
  maxReceiveCount to survive consumer contention.

- **FIFO poison pills block the entire message group.** On a FIFO queue, a
  message that fails processing stays at the head of its message group.
  Messages behind it are not delivered until it is removed (consumed or moved
  to DLQ). A `maxReceiveCount` of 100 on a FIFO queue means up to 100 retry
  cycles where the ENTIRE message group is stalled. DLQ tuning is MORE
  critical for FIFO queues than for standard queues.

- **SSE-SQS (`SqsManagedSseEnabled`) is free and FIPS-validated.** It uses
  AWS-managed key material (rotation handled by SQS, 256-bit AES-GCM). For
  most compliance frameworks (SOC2, PCI-DSS, HIPAA), SSE-SQS satisfies
  at-rest encryption requirements. SSE-KMS (`KmsMasterKeyId`) adds
  customer-managed key control, CloudTrail decrypt logging, and per-API KMS
  cost (~$0.03 per 10k requests). Do NOT flag a queue with SSE-SQS as
  unencrypted — only flag when NEITHER is enabled.

- **`RedriveAllowPolicy` controls who can use a queue as a DLQ.** A DLQ with
  `redrivePermission: "allowAll"` accepts redriven messages from ANY queue
  in the same account. This is a blast-radius concern: a misconfigured
  source queue can flood a shared DLQ, drowning legitimate failed messages.
  `redrivePermission: "byQueue"` with explicit source-queue ARNs is the
  least-privilege pattern.

- **DLQ cross-region is silently rejected at configuration time.** The SQS
  `SetQueueAttributes` API rejects a `RedrivePolicy` whose
  `deadLetterTargetArn` is in a different region. However, if the policy was
  set via CloudFormation drift or a stale config snapshot, the ARN may
  appear in the attribute document without being effective. Always verify
  the DLQ ARN region matches the source queue region.

- **`VisibilityTimeout` x `maxReceiveCount` = effective retry window.** A
  VisibilityTimeout of 30s with maxReceiveCount of 5 gives an effective
  retry window of ~150 seconds before the message hits the DLQ. If the
  consumer's p99 processing time exceeds VisibilityTimeout, the message
  returns to the queue before processing completes, and the receive count
  increments — even though the consumer did not fail. This is the #1 cause
  of false-positive DLQ entries.

- **Lambda event source mapping interaction.** When Lambda consumes SQS, the
  event source mapping calls `DeleteMessage` on successful invocation. If
  the function throws, the message returns after the batch window expires.
  The Lambda service's `MaxBatchingWindowInSeconds` adds delay between
  retries. A `maxReceiveCount` of 3 with Lambda means only ~3 Lambda
  invocations before DLQ — often too few for transient downstream failures.

- **`aws sqs start-message-move-task`** (the current redrive API) moves
  messages from DLQ back to a source queue. It replaced the legacy
  `Redrive` API (deprecated 2022). The task is asynchronous and rate-limited
  — large DLQs take minutes to drain. Do NOT recommend the legacy API.

- **Batch `ReceiveMessage` increments ALL messages' counts.** When using
  `MaxNumberOfMessages > 1`, every message in the batch has its receive
  count incremented at delivery time. If the consumer processes 9 of 10
  successfully but throws on the 10th, all 10 are closer to the DLQ (the 9
  will be deleted on success, but their count was already incremented).

- **Attribute names are case-sensitive.** `aws sqs get-queue-attributes`
  returns `RedrivePolicy`, `KmsMasterKeyId`, `SqsManagedSseEnabled`,
  `MessageRetentionPeriod`, `VisibilityTimeout`, `Policy` — all
  PascalCase. Requesting `redrivePolicy` (lowercase) silently returns
  nothing. When parsing raw API output, match the exact casing.

## Edge-case handling

- **`Principal: "*"` + `aws:SourceArn` (S3/SNS notification pattern).** This
  is the standard cross-service integration pattern and is NOT public
  access. The `aws:SourceArn` condition is set by the AWS service layer
  (S3, SNS, EventBridge) and restricts access to the named resource. Verify
  the SourceArn is a specific bucket/topic ARN, not a wildcard pattern
  (`arn:aws:s3:::*`). Classify as OK for this dimension.

- **`Principal: "*"` + `aws:SourceAccount`.** Same logic — the condition
  restricts access to a specific account. STRONG. Not public.

- **Empty queue policy (`Policy` absent).** This is the SECURE default. With
  no resource-based policy, only IAM identity-based policies govern access.
  Do NOT flag a missing Policy attribute as a gap.

- **DLQ itself has no DLQ.** A dead-letter queue should NOT have its own
  redrive policy (infinite redrive chain). If the DLQ has a RedrivePolicy,
  note as advisory: "DLQ has its own RedrivePolicy — this creates a
  redrive chain. Remove the DLQ's RedrivePolicy."

- **FIFO queue with standard DLQ.** SQS rejects this at configuration time,
  but if the attribute snapshot shows it (stale config), flag as NO_DLQ:
  "FIFO source queue cannot use a standard DLQ — the DLQ must also be FIFO."

- **`RedrivePolicy` with `maxReceiveCount` as integer vs string.** The CLI
  returns `maxReceiveCount` as a string (`"5"`). CloudFormation may set it
  as an integer (`5`). Accept both forms in classification.

- **Multiple statements, some public some not.** The queue-level verdict is
  driven by the **worst** statement. A queue with one safe statement
  (named principal) and one public statement (wildcard, no condition) is
  PUBLIC_ACCESS — the public statement exposes the queue regardless of the
  safe one.

## Recent AWS features (2024-2026)

- **SQS paused queues (2024):** SQS now supports pausing message delivery without deleting messages. Auditors should verify that production queues are not inadvertently paused — a paused queue silently stops message consumption.
- **Message retention period increase (2024):** SQS now supports message retention up to 14 days (previously 4 days). Auditors should verify that retention periods are appropriate — excessive retention on high-throughput queues can cause cost accumulation.
- **SSE-SQS vs SSE-KMS (2024):** SQS now supports server-side encryption with SQS-managed keys (SSE-SQS) as a simpler alternative to SSE-KMS. Auditors should verify which encryption mode is in use — SSE-KMS provides customer-controlled keys but requires KMS key policy management, while SSE-SQS is simpler but less granular.
- **Dead-letter queue redrive (2024-2025):** SQS now supports `StartMessageMoveTask` API for redriving messages from DLQ back to the source queue. Auditors should verify that redrive operations are logged in CloudTrail and that redriven messages do not cause duplicate processing.

