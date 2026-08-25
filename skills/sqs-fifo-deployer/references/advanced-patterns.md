# Advanced Patterns — sqs-fifo-deployer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## Mindset

**One-line takeaway:** An SQS FIFO queue guarantees first-in-first-out
ordering within a message group. The message group ID is the
partitioning key — messages with the same group ID are processed in
order; messages with different group IDs are processed in parallel.
Deduplication prevents duplicate messages within the 5-minute
deduplication window, either by content hash (content-based) or by
explicit deduplication ID. High-throughput FIFO mode increases the
queue's throughput by decoupling deduplication from the queue level,
enabling per-message-group deduplication.

Three misconceptions dominate SQS FIFO misdesign at provisioning time:

- **"FIFO queues are just like Standard queues with ordering."** They
  are fundamentally different. FIFO queues require the `.fifo` suffix
  in the queue name. They require FifoQueue=true at creation (immutable
  attribute — a Standard queue CANNOT be converted to FIFO). They
  enforce per-message-group ordering. They have lower throughput than
  Standard queues (3,000 messages/second with batching, or 300 TPS
  per API action) unless high-throughput mode is enabled. They support
  deduplication. Standard queues support none of these.

- **"Message group ID is just a label."** It is the ordering partition.
  Messages within the same group ID are strictly ordered. Messages
  with different group IDs can be processed in parallel, enabling
  throughput scaling. The number of in-flight message groups directly
  determines the achievable parallelism. A single message group ID
  serializes ALL messages through one consumer. Choosing the right
  partitioning key (like a database entity ID) is critical for both
  correctness (ordering) and performance (parallelism).

- **"Deduplication and high-throughput mode are independent."** They
  are coupled. Content-based deduplication hashes the message body to
  generate a deduplication ID. This works at the QUEUE level — all
  messages, regardless of group, share the deduplication window.
  High-throughput FIFO mode (DeduplicationScope=messageGroup,
  ThroughputLimit=messagesPerGroupId) moves deduplication to the
  MESSAGE GROUP level, enabling 300 TPS per API action per message
  group (instead of per queue). Enabling high-throughput mode without
  understanding the deduplication scope change can cause unexpected
  duplicate messages.

## Step 11 — Recent features

**Recent AWS features (2023-2026):**

- **High-throughput FIFO mode (2023-2024):** AWS introduced
  DeduplicationScope and ThroughputLimit attributes, enabling per-
  message-group throughput scaling. This removed the per-queue 300 TPS
  bottleneck for FIFO queues.

- **StartMessageMoveTask API (2023-2024):** The modern API for moving
  messages from a DLQ back to the source queue, replacing the custom
  Lambda-based redrive patterns. Preserves message attributes and
  supports partial moves.

- **SSE-KMS for SQS (maturity 2023-2024):** Full SSE-KMS support for
  FIFO queues, including cross-account KMS key usage and
  KmsDataKeyReusePeriodSeconds tuning.

- **FIFO queue visibility timeout per-message (2023-2024):**
  Enhanced ChangeMessageVisibility API for per-message timeout
  adjustments, enabling dynamic timeout based on message processing
  complexity.

- **Terraform provider improvements (2023-2024):** The Terraform
  `aws_sqs_queue` resource now supports DeduplicationScope,
  ThroughputLimit, KmsMasterKeyId, and redrive_policy attributes with
  full lifecycle management.

- **Cross-account DLQ redrive (2024-2025):** AWS enhanced the
  StartMessageMoveTask to support cross-account DLQ redrive, allowing
  DLQs in one account to redrive to source queues in another account
  with proper IAM permissions.
