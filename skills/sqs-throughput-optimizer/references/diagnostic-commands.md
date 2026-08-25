# Diagnostic Commands — sqs-throughput-optimizer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval. Do NOT execute until confirmed.
- **Test attribute changes in staging first.** Changing
  ReceiveMessageWaitTimeSeconds or VisibilityTimeout affects all
  consumers immediately.
- **Verify FIFO mode compatibility before enabling high-throughput.**
  `DeduplicationScope=MessageGroup` breaks cross-group dedup.
- **ESM changes are immediate.** Consumer must handle the new batch size
  without OOM or timeout.
- **Visibility timeout increase is safe; decrease is risky.** Decreasing
  may cause re-deliveries if the consumer is slower than the new timeout.
- **Redrive destination must exist.** Verify the target queue ARN before
  starting `StartMessageMoveTask`.
- **SSE-KMS changes break message access.** Plan a drain-and-re-encrypt
  migration before rotating KMS keys.
- **Bulk-operation limit:** Process at most 5 queues per batch. Abort if
  any queue shows increased ApproximateAgeOfOldestMessage post-change.
