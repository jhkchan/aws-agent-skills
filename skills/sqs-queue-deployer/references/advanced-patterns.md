# Advanced Patterns — sqs-queue-deployer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## Latest SQS features (2024-2026)

- **SQS partial batch responses (Lambda):** report per-message failures; only failed messages retried. Enable via `--function-response-types ReportBatchItemFailures`.
- **High-throughput FIFO (1500 TPS):** per-message-group throughput limiting via `FifoThroughputLimit=perMessageGroupId` + `DeduplicationScope=messageGroup`.
- **No-SQL payload in message attributes:** structured attributes for filtering without parsing the body.
- **Message retention max 14 days** (more prominently used for DLQs).
- **SSE-SQS:** Free, FIPS-validated AES-256-GCM. Recommended default.
- **StartMessageMoveTask API:** Current API for redriving from DLQ back to source. Replaced deprecated legacy `Redrive` API.

## Edge-case handling

- **FIFO queue with all messages using the same `MessageGroupId`.** Degrades to a single-message-in-flight serial pipeline — throughput drops to 300 TPS (standard) or 10 TPS per group (high-throughput). Detection: `ApproximateNumberOfMessagesNotVisible` rising while `NumberOfEmptyReceives` is high. Fix: shard `MessageGroupId` (e.g., `order-{customer_id}`).
- **FIFO dedup scope collision after high-throughput mode change.** Switching to `DeduplicationScope=messageGroup` changes dedup from queue-scoped to group-scoped. Messages in different groups that previously deduplicated no longer do. Fix: ensure producers set explicit `MessageDeduplicationId`.
- **Lambda event source mapping `BatchSize` > 1 without `ReportBatchItemFailures`.** A single failed message causes all 10 to retry. Fix: enable `FunctionResponseTypes: [ReportBatchItemFailures]`.
- **Cross-account queue access with SSE-KMS.** Both the queue policy AND the KMS key policy must grant the foreign account. Without both, fails with `KMSAccessDeniedException`.
- **Redrive from DLQ back to FIFO source.** `StartMessageMoveTask` preserves original `MessageGroupId`. Deduplication applies — if original `DeduplicationId` is within the 5-min window, the redriven message is silently dropped.
- **Queue policy size limit is 64 KiB.** Use IAM identity-based policies for same-account access instead of growing the resource-based policy.
