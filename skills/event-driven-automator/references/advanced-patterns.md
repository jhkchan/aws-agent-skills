# Advanced Patterns

Blocks moved verbatim from SKILL.md in the agentskills.io progressive-disclosure
restructure. No content changed; load when a SKILL.md pointer stub applies.

## Mindset (moved from SKILL.md)

**One-line takeaway:** an event-driven workflow on EventBridge is
**at-least-once delivery over an unordered (or partition-ordered)
async bus** — every design choice (DLQ, idempotency, retry, ordering,
circular-dependency guard) flows from that one fact. A workflow
without a DLQ is a workflow that silently loses events; a consumer
without idempotency is a consumer that double-charges, double-creates,
and double-notifies.

- **EventBridge is the routing layer, not the execution layer.** It
  matches events to rules and dispatches to targets. The targets do
  the work. A misconfigured rule (too narrow → events missed; too
  broad → fan-out storm) is the most common failure.
- **At-least-once means exactly-once must be enforced by the
  consumer.** EventBridge may deliver the same event twice
  (retried delivery, regional failover, replay). Consumers MUST be
  idempotent — typically via a deduplication ID hashed from event
  fields and stored in DynamoDB with a conditional write.
- **Ordering is per-partition, not global.** Within a partition
  (e.g., a DynamoDB shard, a Kinesis shard), EventBridge preserves
  order. Across partitions, ordering is not guaranteed. Workflows
  that require global ordering must serialize via a single-partition
  fan-in.

## Step 0: Expert knowledge — non-obvious EventBridge behaviors (moved from SKILL.md)

- **EventBridge delivers at-least-once, not exactly-once.** Retries,
  regional failover, replay (via archive), and target throttling can
  all produce duplicate deliveries. Idempotent consumers are not
  optional.

- **`PutEvents` is the only API that ingests events.** Every
  EventBridge workflow begins with a `PutEvents` call (from an AWS
  service, an application, or a partner). The bus policy controls
  who can call `PutEvents`. See the
  `eventbridge-bus-policy-auditor` skill for ingestion-gate audit.

- **Rule `EventPattern` is JSONPath-like, not full JSONPath.** It
  supports exact match, prefix, suffix, contains, equals-ignore-case,
  numeric ranges, and CIDR matching. It does NOT support arbitrary
  JSONPath expressions. Complex filters must be done in the consumer.

- **`InputTransformer` reshape is per-target.** A rule can have up
  to 5 targets, each with its own input transformer. The original
  event payload is NOT passed to the target unless the transformer
  explicitly maps it.

- **Retry policy is per-target.** `RetryPolicy` on
  `put-targets` controls `MaximumRetryAttempts` and
  `MaximumEventAgeInSeconds`. Defaults: 185 retries (24 hours for
  API destinations, 6 hours for others). A target without an
  explicit retry policy uses defaults.

- **Same-bus same-account PutEvents does not require a bus policy.**
  Same-account access is implicit (root of trust). The bus policy
  gates cross-account and service-principal delegation.

- **EventBridge Pipes is a separate API surface from rules.** Pipes
  connect a source (DynamoDB Streams, Kinesis, SQS, MQ, MSK,
  self-managed Kafka) to a target with optional filtering and
  enrichment (Lambda, Step Functions, API destination, Batch, ECS
  task). Pipes are for stream/queue fan-out, NOT for matching
  arbitrary events on a bus.

- **EventBridge Scheduler is a separate service for time-based
  triggers.** It does not use rules. Each schedule is a first-class
  resource with its own IAM role, target, and timeframe. Use it
  instead of cron-style EventBridge rules for per-schedule management.

- **`TestEventPattern` is your test fixture.** It validates a
  pattern against a sample event without creating the rule. Always
  run `test-event-pattern` before `put-rule` to confirm the match.

- **Rule quotas: 300 rules per bus, 5 targets per rule.** A
  high-volume workflow with many filtered sub-routes hits the cap.
  Consider fan-out to SQS for finer-grained per-consumer filtering.

- **API destinations rate-limit per connection.** A target API
  destination has a per-connection rate limit (default 300 TPS). A
  burst of events above the limit is buffered up to the
  `InvocationRateLimitPerSec` cap; sustained excess is dropped to
  DLQ.

- **`PutEvents` accepts up to 10 events per API call, 256 KB per
  event, 2 MB total request.** Application publishers must batch for
  throughput and respect the size cap. Events over 256 KB must be
  parked in S3 and referenced by URI.

- **Cross-region delivery is NOT default.** EventBridge rules are
  regional. To route events cross-region, use a global endpoint or
  fan-out to an SNS topic with cross-region subscriptions, or use
  `PutEvents` with a region-specific bus ARN.

- **Schema Registry auto-discovery captures schemas only on the
  default bus by default.** Custom-bus schema discovery must be
  explicitly enabled. Undiscovered schemas cannot be code-generated.

- **Archives capture events for replay but are NOT backups.** Replay
  re-publishes events to ALL rules matching the archive pattern,
  including rules created AFTER the original events. This can cause
  unexpected duplicate processing.

## Step 7: EventBridge Pipes (moved from SKILL.md)

Use Pipes when the source is a stream or queue (DynamoDB Streams,
Kinesis, SQS, MQ, MSK, self-managed Kafka). Pipes differ from rules:
the source is a pollable resource, not a published event.

```bash
aws pipes create-pipe \
  --name orders-pipe \
  --source arn:aws:dynamodb:us-east-1:111111111111:table/Orders/stream/2026-08-01 \
  --source-parameters '{"DynamoDBStreamParameters":{"StartingPosition":"LATEST","BatchSize":10,"MaximumBatchingWindowInSeconds":5}}' \
  --target arn:aws:lambda:us-east-1:111111111111:function:process-order \
  --target-parameters '{"LambdaFunctionParameters":{"InvocationType":"REQUEST_RESPONSE"}}' \
  --role-arn arn:aws:iam::111111111111:role/service-role/EventBridge-Pipe-Role \
  --filter-pattern '{"dynamodb": {"NewImage": {"status": {"S": [{"prefix": "PAID"}]}}}}'
```

Pipes support optional enrichment (Lambda, Step Functions, API
destination) between source and target for transformation.

| Dimension | Rule-based | Pipes |
|---|---|---|
| Source | Event bus | DynamoDB Streams, Kinesis, SQS, MQ, MSK |
| Filtering | EventPattern | FilterCriteria (similar syntax) |
| Enrichment | InputTransformer | Lambda / SFN / API destination in-between |
| Use case | Service event routing | Stream/queue fan-out |

After creating, start the pipe:

```bash
aws pipes start-pipe --name orders-pipe
aws pipes describe-pipe --name orders-pipe --query 'CurrentState'
```

## Step 8: EventBridge Scheduler (moved from SKILL.md)

For time-based triggers, prefer Scheduler over cron-style rules.
Each schedule is a first-class resource with its own role.

```bash
aws scheduler create-schedule \
  --name nightly-report \
  --schedule-expression 'cron(0 2 * * ? *)' \
  --flexible-time-window '{"Mode": "OFF"}' \
  --target '{"Arn":"arn:aws:lambda:us-east-1:111111111111:function:nightly-report","RoleArn":"arn:aws:iam::111111111111:role/service-role/Scheduler-Invoke-Lambda"}' \
  --description "Nightly report at 02:00 UTC"
```

Trade-offs:

| Dimension | EventBridge rule (cron) | EventBridge Scheduler |
|---|---|---|
| Per-schedule management | Limited | First-class resource, individual update/delete |
| Schedule count quota | 300 rules per bus | 1M schedules per account |
| Timezone | UTC only | UTC plus tz library |
| Start/stop windows | Not supported | `StartDate`/`EndDate`/`ScheduleExpression` |
| One-time schedules | Hack (rate + delete) | Native via `StartDate == EndDate` |

For any new time-based workflow, default to Scheduler unless you need
event-pattern matching.

## Step 9: Global endpoints — multi-region failover (moved from SKILL.md)

For regional-failure-resilient workflows:

```bash
aws events create-endpoint \
  --name orders-failover \
  --routing-config '{"FailoverConfig":{"Primary":{"HealthCheck":"arn:aws:route53:...:healthcheck/primary"},"Secondary":{"RouteDetails":{"HealthCheck":"arn:aws:route53:...:healthcheck/secondary"}}}}' \
  --event-buses '[{"EventBusArn":"arn:aws:events:us-east-1:111111111111:event-bus/orders"},{"EventBusArn":"arn:aws:events:us-west-2:111111111111:event-bus/orders"}]'
```

The endpoint ARN is used as the target for producers. Route53
health checks drive failover. The replication is asynchronous — a
few seconds of lag during failover.

Requirements:
- Both buses must have equivalent rules and targets.
- Both buses must have equivalent bus policies, DLQs, KMS keys.
- Schema Registry and archives are per-region — replicate separately.

## Appendix A — Event pattern operators (moved from SKILL.md)

| Operator | JSON form | Matches when |
|---|---|---|
| Exact | `["v1", "v2"]` | Field equals any listed value |
| Prefix | `{"prefix": "ord-"}` | Field starts with prefix |
| Suffix | `{"suffix": "-prod"}` | Field ends with suffix |
| Contains | `{"contains": ["error"]}` | Field contains substring (case-sensitive) |
| Equals-ignore-case | `{"equals-ignore-case": "true"}` | Case-insensitive match |
| Numeric | `{"numeric": [">=", 7]}` | Numeric comparison; supports `>`, `>=`, `<`, `<=`, `=`, ranges |
| CIDR | `{"cidr": "10.0.0.0/8"}` | IP address in CIDR block |
| Exists | `{"exists": true}` | Field is present (or `false` for absent) |
| Anything-but | `{"anything-but": ["dev"]}` | Field is anything except listed values |

Combine operators with nested JSON. EventBridge matches ALL specified
fields (AND). For OR within a field, use a list.

## Appendix B — Common AWS event patterns (moved from SKILL.md)

| Source | Detail-type | Common filter | Typical target |
|---|---|---|---|
| `aws.ec2` | `EC2 Instance State-change Notification` | `detail.state=["running"]` | Lambda auto-tagger |
| `aws.guardduty` | `GuardDuty Finding` | `detail.severity>=7` | Lambda isolate-instance |
| `aws.securityhub` | `Security Hub Findings - Imported` | `detail.findings[].Severity.Label=["CRITICAL","HIGH"]` | Step Functions workflow |
| `aws.codebuild` | `CodeBuild Build State Change` | `detail.build-status=["FAILED"]` | SNS + Lambda notify |
| `aws.autoscaling` | `EC2 Instance Launch Successful` | — | Lambda register-to-target-group |
| `aws.s3` | `Object Created` | `detail.object.key=[{"prefix":"uploads/"}]` | Lambda trigger-processing |
| `aws.cloudwatch` | `CloudWatch Alarm State Transition` | `detail.stateName=["ALARM"]` | SNS → Lambda ack |
| `aws.signin` | `AWS Console Sign In` | `detail.eventName=["ConsoleLogin"]`, `detail.responseElements.ConsoleLogin=["Success"]` | Lambda alert on new MFA-disabled logins |
| `aws.iam` | `AWS API Call via CloudTrail` | `detail.eventName=["DeleteRole"]` | Lambda revert or alert |

For AWS service events on the default bus, the `detail` field shape
varies by service — consult the service's EventBridge documentation.

## Recent AWS features 2024-2026 (moved from SKILL.md)

- **EventBridge global endpoints GA (2024):** Automatic regional
  failover for event buses. Requires matching rules and targets on
  the secondary bus; verify before failover.

- **EventBridge Scheduler (2024-2025):** First-class time-based
  scheduling with per-schedule IAM roles, timezones, and one-time
  schedules. Preferred over cron-style EventBridge rules for any
  new time-based workflow.

- **EventBridge Pipes enhancements (2024):** Added support for
  self-managed Kafka, MSK, and improved enrichment (Lambda, Step
  Functions, API destination, Batch, ECS). Pipes are now the
  standard path for stream/queue fan-out.

- **Schema Registry updates (2024):** OpenAPI and JSON Schema
  support. Discover schemas on custom buses explicitly — auto-
  discovery only applies to the default bus.

- **EventBridge API destinations improvements (2024-2025):**
  Enhanced credential management for OAuth client-credentials. API
  key and basic-auth credentials still do NOT auto-rotate —
  monitor `InvocationHttpStatusCode` for stale credentials.

- **`PutEvents` batch size and EntrySize limits (2024):** Still
  10 entries per call, 256 KB per entry. Events over 256 KB must
  be parked in S3 and referenced by URI.
