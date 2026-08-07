# EventBridge Targets and Retry Reference

Supplementary reference for the Event-Driven Automator skill. Use when
selecting a target type, configuring retry policy, wiring DLQ, or
debugging a delivery failure.

## Target type comparison

| Target | Sync/Async | Default retry | Native DLQ | Invocation |
|---|---|---|---|---|
| **Lambda** | Async | 185 attempts / 6h | Via target DeadLetterConfig | `lambda:InvokeFunction` |
| **Step Functions** | Async | 185 attempts / 24h | Via target DeadLetterConfig | `states:StartExecution` |
| **SQS** | Async | 185 attempts / 6h | Via target DeadLetterConfig | `sqs:SendMessage` |
| **SNS** | Async | 185 attempts / 6h | Via target DeadLetterConfig | `sns:Publish` |
| **ECS task** | Async | 185 attempts / 6h | Via target DeadLetterConfig | `ecs:RunTask` |
| **Systems Manager** | Async | 185 attempts / 6h | Via target DeadLetterConfig | `ssm:StartAutomationExecution` |
| **Batch** | Async | 185 attempts / 6h | Via target DeadLetterConfig | `batch:SubmitJob` |
| **API destination (HTTP/S)** | Async | Per `MaximumRetryAttempts` (default 3) | Via target DeadLetterConfig | HTTP POST |
| **API Gateway** | Async | 185 attempts / 6h | Via target DeadLetterConfig | `apigateway:POST` |
| **Redshift Data API** | Async | 185 attempts / 6h | Via target DeadLetterConfig | `redshift-data:ExecuteStatement` |
| **Kinesis Firehose** | Async | 185 attempts / 6h | Via target DeadLetterConfig | `firehose:PutRecord` |

For ALL target types: ALWAYS configure explicit `RetryPolicy` and
`DeadLetterConfig`. Defaults are usually too aggressive (185 retries
over hours).

## Retry policy semantics

| Field | Meaning | Default |
|---|---|---|
| `MaximumRetryAttempts` | Total retries after initial attempt | 185 (most targets); 3 for API destinations |
| `MaximumEventAgeInSeconds` | Max age of event for retry | 86400 (24h) |

Exponential backoff: EventBridge retries with exponential backoff
plus jitter. The first retry happens within seconds; subsequent
retries grow to minutes and then hours. The full retry window is
bounded by `MaximumEventAgeInSeconds`.

Tuning by workload:

| Workload | RetryAttempts | EventAge | Rationale |
|---|---|---|---|
| User-facing notification (Slack, email) | 3 | 900s (15m) | A 24h-old notification is worse than no notification |
| Compliance audit (must not lose) | 185 (default) | 86400s | Persistence over latency |
| API destination with rate-limited endpoint | 5 | 3600s | Allow backoff but bound it |
| Step Functions long-running workflow | 2 | 86400s | SFN handles its own internal retries |
| Lambda with idempotent consumer | 5 | 3600s | Trust idempotency; bound the retry storm |

## DLQ wiring

DLQ is per-target via `DeadLetterConfig.arn`. The DLQ MUST be a
SQS queue (not SNS, not Kinesis). EventBridge delivers the original
event envelope to the DLQ after exhausting retries.

```bash
aws sqs create-queue --queue-name eventbridge-<rule>-dlq
aws sqs set-queue-attributes \
  --queue-url https://sqs.<region>.amazonaws.com/<account>/eventbridge-<rule>-dlq \
  --attributes MessageRetentionPeriod=1209600
aws events put-targets --rule <rule> --event-bus-name <bus> \
  --targets '[{"Id":"<id>","Arn":"<target-arn>","DeadLetterConfig":{"Arn":"arn:aws:sqs:<region>:<account>:eventbridge-<rule>-dlq"},"RetryPolicy":{"MaximumRetryAttempts":3,"MaximumEventAgeInSeconds":900}}]'
```

Always set the SQS retention period to 14 days (1209600s) max to
give operators time to triage. Default 4 days is too short for
most operational response.

## Lambda invocation permission

Required after `put-targets`:

```bash
aws lambda add-permission \
  --function-name <fn> \
  --statement-id EventBridgeInvoke-<rule> \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:<region>:<account>:rule/<bus>/<rule> \
  --source-account <account>
```

Verify:

```bash
aws lambda get-policy --function-name <fn> --query 'Policy' --output text \
  | jq '.Statement[] | select(.Principal.Service=="events.amazonaws.com")'
```

A missing or revoked permission produces silent non-delivery (events
match the rule but the Lambda is never invoked). The error surfaces
in CloudTrail as `AccessDenied` from `events.amazonaws.com`, not in
EventBridge metrics.

## Common delivery failures and fixes

| Symptom | Cause | Fix |
|---|---|---|
| Rule matches (TestEventPattern OK) but target never invoked | Missing Lambda invocation permission | `lambda:AddPermission` for `events.amazonaws.com` |
| Target invoked once then no more | DLQ ARN does not exist (put-targets accepts bad ARN silently) | Create the DLQ first |
| DLQ fills with valid events | Consumer throwing on every invocation | Inspect Lambda logs; fix the consumer bug |
| DLQ fills with throttling errors | Target throttled (Lambda concurrency = 0) | Provision concurrency or switch to SQS buffer |
| Events delivered multiple times | At-least-once delivery; no idempotency | Implement dedup in consumer (DynamoDB conditional write) |
| Events arrive out of order | No global ordering guarantee | Serialize via SQS FIFO or single-shard stream |
| API destination 4xx errors | OAuth token expired or API key rotated | Re-authorize the connection |
| Replay produces unexpected duplicates | Replay sends archived events to ALL matching rules, including new ones | Pause new rules before replay |

## Debugging checklist

1. `describe-rule` — is the rule ENABLED?
2. `test-event-pattern` — does the pattern match a known sample?
3. `list-targets-by-rule` — are targets wired?
4. `lambda get-policy` — is the invocation permission set?
5. CloudTrail `InvokeFunction` events — is the target being called?
6. Lambda logs — is the target throwing?
7. SQS DLQ depth — are events accumulating in the DLQ?
8. CloudWatch metrics `Invocations`, `FailedInvocations`,
   `ThrottledRules` — where in the pipeline is the failure?

## Quotas to plan around

| Resource | Quota |
|---|---|
| Rules per event bus | 300 |
| Targets per rule | 5 |
| `PutEvents` entries per request | 10 |
| `PutEvents` request size | 2 MB |
| Single event size | 256 KB |
| API destination invocations per second per connection | 300 (default; adjustable) |
| Pipes per account per region | 200 (soft) |
| Scheduler schedules per account | 1,000,000 |
| Replay concurrent per account | 1 |

For high-volume workflows that exceed these quotas, fan out to SQS
or Kinesis for finer-grained consumer routing.
