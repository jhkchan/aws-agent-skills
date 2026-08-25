# Advanced Patterns

Blocks moved verbatim from SKILL.md in the agentskills.io progressive-disclosure
restructure. No content changed; load when a SKILL.md pointer stub applies.

## Mindset (moved from SKILL.md)

**One-line takeaway:** an EventBridge Pipe is a **point-to-point
stream processor** — one source, one target, optional filter +
enrichment in between. Unlike an EventBridge rule (which is a fan-out
dispatcher from a bus), a Pipe pulls records from a source on the
Pipe's own concurrency, optionally transforms them, and delivers them
to exactly one target. Pipes own the polling, batching, retry, and DLQ.

Three facts make Pipe provisioning different from "trigger Lambda on
stream events":

- **The Pipe is the poller — not the target.** For DynamoDB Streams
  and Kinesis sources, you do NOT attach the Lambda trigger directly.
  The Pipe's IAM role reads from the stream; the Pipe delivers batches
  to the target. Two independent permissions are required: the Pipe
  role reads the source, the target resource policy allows the Pipe
  role to invoke it. Skipping the target resource policy is the most
  common failure.

- **Batch window behavior is source-dependent.** For streaming sources
  (DynamoDB Streams, Kinesis, MSK, MQ, self-managed Kafka),
  `MaximumBatchingWindowInSeconds` (0-300s) controls how long the Pipe
  waits to assemble a batch before invoking the target. For SQS sources
  the window is ignored — SQS already has its own `VisibilityTimeout`
  and `ReceiveMessage` semantics. Set `MaximumBatchSize` (1-10000,
  source-specific cap) and `MaximumRecordAgeInSeconds` (60-86400s) to
  bound batch behavior.

- **Enrichment and target are separate stages with separate
  permissions.** The enrichment step (Lambda, Step Functions, API
  Gateway, API Destination) transforms the batched payload before it
  reaches the target. The Pipe role needs `lambda:InvokeFunction` (or
  equivalent) on the enrichment AND a separate grant on the target.
  Each stage has its own retry policy; enrichment failures do NOT
  automatically replay to the DLQ unless the Pipe's `OnPartialBatchItemFailure`
  is configured for SQS/Kinesis sources.

## Step 0: Expert knowledge — non-obvious Pipe behaviors (moved from SKILL.md)

- **The Pipe is the poller — the target's trigger config is NOT used.**
  For DynamoDB Streams → Lambda, you do NOT call
  `lambda create-event-source-mapping`. The Pipe role reads the stream
  and invokes Lambda. The Lambda does NOT have a direct AWS::Lambda::EventSourceMapping.

- **Two independent permissions are required per pipe.** (a) The pipe
  role reads from the source (`dynamodbstreams:GetRecords` or
  `sqs:ReceiveMessage` or `kinesis:GetRecords` or `kafka-cluster:ReadData`).
  (b) The target resource policy allows the pipe role (or
  `pipes.amazonaws.com`) to invoke. Lambda / Step Functions / API
  Gateway targets accept resource-based policies; SQS / SNS / ECS
  require the pipe role to have the action in its identity-based policy.

- **`MaximumBatchingWindowInSeconds` is ignored for SQS sources.** SQS
  already controls visibility and receipt semantics. For SQS source,
  set the source queue's `VisibilityTimeout` to at least 6x the target
  Lambda timeout (standard Lambda event-source mapping rule). For
  streaming sources, the batching window controls how long the Pipe
  waits to gather records before invoking.

- **DLQ behavior differs by source type.** For DynamoDB Streams,
  Kinesis, MSK, Amazon MQ, and self-managed Kafka: the pipe DLQ receives
  records that exceed retry or record-age limits. For SQS source: the
  DLQ is on the **source queue** (configured via `RedrivePolicy`); the
  pipe-level `DeadLetterConfig` is ignored for SQS. Configure both
  correctly or your poison-pill messages disappear.

- **Enrichment runs on the BATCHED payload, not individual records.**
  The enrichment Lambda receives the full batch in one invocation. If
  it throws, the entire batch is retried. Use enrichment for batch
  transformations (e.g., join records, schema reshape, enrichment
  lookup) — NOT for per-record validation (use the target Lambda for that).

- **MSK / self-managed Kafka require explicit `ConsumerGroupID`.** Two
  pipes sharing a consumer group split partitions between them. Two
  pipes with different consumer groups both receive all records. Pick
  the consumer group deliberately — wrong choice silently halves or
  duplicates throughput.

- **Filter pattern runs on the source's raw payload, BEFORE enrichment.**
  For DynamoDB Streams the filter matches the `dynamodb.NewImage` /
  `OldImage` fields. For SQS it matches the `body` (JSON-parsed). For
  Kinesis it matches the decoded record. Malformed patterns silently
  filter everything — always validate with `test-event-pattern` style
  dry-run before deploying.

- **`OnPartialBatchItemFailure` controls partial failure behavior for
  SQS and Kinesis/DDB sources (2024+).** `AUTOMATIC_BISECT` splits the
  batch in half on failure (helps isolate poison records). Set this
  when working with large batches where one bad record should not
  reprocess the whole batch.

## Expert heuristic: when to use enrichment vs. inline target Lambda (moved from SKILL.md)

The enrichment stage is optional. The heuristic below resolves whether
to put transformation logic in an enrichment Lambda or in the target
Lambda itself.

| Signal | Choose |
|---|---|
| Transformation reuses the same lookup/join across multiple pipes | Enrichment Lambda (DRY, one function reused) |
| Transformation is per-record validation with selective drop | Target Lambda (enrichment can't drop individual records) |
| Transformation is schema reshape for a Step Functions target | Enrichment Lambda (Step Functions input must be shaped correctly) |
| Transformation is a synchronous external API call | API Destination enrichment (no code) or API Gateway enrichment (existing endpoint) |
| Transformation + business logic are coupled in one function | Target Lambda (skip enrichment, keep it simple) |
| Multiple stages needed (e.g., lookup + transform + validate) | Step Functions enrichment (Express Workflow for sync) |
| Cost optimization: large batches vs. fine-grained invocations | Enrichment reduces target invocations when multiple records can be coalesced into one target call |

**Decision rules:**

- Default: target Lambda only. Add enrichment when (a) the same
  transformation is used across 2+ pipes, OR (b) the target is Step
  Functions / Batch / Redshift / SageMaker and needs pre-shaped input.
- Enrichment Lambda runs on the **batched payload** — it can drop
  records only by returning a smaller batch, not by selectively
  filtering per record across retry boundaries.
- For API Gateway / API Destination enrichment, the external endpoint
  must return within the pipe's batch window or the batch fails.
- Enrichment failures retry the ENTIRE batch — keep enrichment logic
  idempotent.

ALWAYS emit the enrichment decision as a PRE_CHECKS row naming the
enrichment ARN, target ARN, and the rationale (DRY, schema-reshape,
cost).

## Recent AWS features 2024-2026 (moved from SKILL.md)

- **AWS Batch target (2024-2025):** EventBridge Pipes supports AWS Batch
  job queues as a target. Pipe submits a Batch job per batched payload
  — enables event-driven batch processing without a separate consumer
  Lambda. Pipe role requires `batch:SubmitJob` plus `iam:PassRole` on
  the job role.

- **Enrichment transformations (2024-2025):** documented patterns for
  enrichment Lambda returning a transformed batch payload. Useful for
  fan-in (joining customer data before target invocation), schema
  reshape (CSV → JSON for Step Functions), or coalescing (multiple
  records → one target call to reduce invocations).

- **OnPartialBatchItemFailure `AUTOMATIC_BISECT` (2024):** for DynamoDB
  Streams, Kinesis, and SQS sources, the pipe automatically bisects a
  failing batch to isolate poison records — prevents one bad record
  from blocking the whole batch.

- **Self-managed Kafka source (2024):** Pipes can consume from
  self-managed Kafka clusters (including MSK Serverless, Confluent
  Cloud, on-prem clusters via VPC). Requires `ServerRootCA`,
  `VpcSubnets`, `SecurityGroups`, and `AuthType`.

- **Amazon MQ source (2023-2024):** Pipes consume from Amazon MQ
  ActiveMQ and RabbitMQ brokers. Requires Secrets Manager credentials
  secret with `username`/`password` keys.

- **Redshift and SageMaker targets (2024):** Pipes can write directly
  to Redshift (Serverless or Provisioned) via the Redshift Data API
  and trigger SageMaker Pipelines. Enables event-driven ML inference
  and data ingestion without Lambda glue.

- **API Destination target and enrichment (2024):** Pipes can invoke
  API Destinations as enrichment (pre-transform via external HTTPS) or
  as target (fan-out to external webhook). Requires Connection resource
  with auth config.
