# Advanced Patterns — SNS Topic Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Latest SNS features (2024-2026)

- **SNS message archiving (Direct Messaging):** Archive messages to S3 via
  Kinesis Data Firehose for long-term storage and replay.
- **SNS-to-EventBridge integration:** Route messages directly to EventBridge
  event buses for event-driven architectures.
- **Message body filter policy (GA):** `FilterPolicyScope=MessageBody` for
  payload-based subscription filtering. Requires JSON message bodies.
- **SNS message data protection (2024):** Detect and block sensitive data
  (PII, financial) in published messages. Per-topic deny/redact actions.
- **FIFO topic delivery status logging (2024-2025):** Enhanced per-protocol
  failure logging for FIFO topics.
- **SNS-to-SQS SSE-KMS consistency (2024):** Topic KMS key policy must grant
  `kms:Decrypt` to the SQS queue's consumer role.

## Workload-specific deployment matrix

| Workload | Topic type | Encryption | Subscribers | Filter | DLQ | Delivery logging |
|---|---|---|---|---|---|---|
| **Event fan-out** | Standard | AWS-managed | SQS (multiple) | Per-service attributes | Per-subscription | SQS failure |
| **Ordered processing** | FIFO | AWS-managed | SQS FIFO | N/A | Per-subscription | SQS failure |
| **Webhook delivery** | Standard | AWS-managed | HTTP/HTTPS | N/A | Per-subscription | HTTP failure (REQUIRED) |
| **Cross-account fan-out** | Standard | Customer CMK | SQS (cross-account) | MessageAttributes | Per-subscription | SQS failure |
| **Mobile push** | Standard | AWS-managed | Application | N/A | Per-subscription | Application failure |
| **S3 Event fan-out** | Standard | AWS-managed | SQS, Lambda | Per-event-type | Per-subscription | SQS failure |
