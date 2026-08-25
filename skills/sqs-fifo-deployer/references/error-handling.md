# Error Handling — sqs-fifo-deployer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## Error handling

- **Message not delivered:** ensure `MessageGroupId` is included on
  every send. If `ContentBasedDeduplication=false`, ensure
  `MessageDeduplicationId` is also included.
- **Duplicate processing:** visibility timeout may be too short —
  increase to at least 2x processing time. Or content-based dedup is
  not catching logical duplicates — switch to explicit dedup ID.
- **Throughput limit hit:** standard FIFO is limited to 300 TPS per
  API action. Enable high-throughput mode or distribute message groups.
- **DLQ attachment fails:** the DLQ must be a FIFO queue. Standard
  DLQs are rejected for FIFO main queues.
- **Cross-account delivery fails:** verify both the queue access policy
  grants `sqs:SendMessage` to the producer account AND the producer's
  IAM role permits it. If SSE-KMS, the key policy must allow the
  producer account.
