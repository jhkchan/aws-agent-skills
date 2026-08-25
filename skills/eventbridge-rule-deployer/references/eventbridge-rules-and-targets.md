# EventBridge Rules and Targets Reference

Supplementary reference for the EventBridge Rule Deployer skill. Use
when picking a rule type, writing an event pattern, wiring a target,
configuring retry/DLQ, or debugging a deployment.

## Rule types comparison

| Dimension | Event-pattern rule | Schedule rule |
|---|---|---|
| Trigger | Matching event on bus | Cron/rate expression |
| Source flag | `--event-pattern` JSON | `--schedule-expression` string |
| Use case | Event-driven automation | Time-based job |
| Modern alternative | n/a | EventBridge Scheduler |
| State field | `ENABLED` / `DISABLED` | `ENABLED` / `DISABLED` |
| Targets per rule | 5 | 5 |

## Event pattern operators (full reference)

| Operator | JSON form | Matches when |
|---|---|---|
| Exact | `["v1", "v2"]` | Field equals any listed value |
| Prefix | `{"prefix": "ord-"}` | Field starts with prefix |
| Suffix | `{"suffix": "-prod"}` | Field ends with suffix |
| Contains | `{"contains": ["error"]}` | Field contains substring (case-sensitive) |
| Equals-ignore-case | `{"equals-ignore-case": "true"}` | Case-insensitive match |
| Numeric | `{"numeric": [">=", 7]}` | Numeric; supports `>`, `>=`, `<`, `<=`, `=`, ranges |
| CIDR | `{"cidr": "10.0.0.0/8"}` | IP address in CIDR block |
| Exists | `{"exists": true}` | Field is present (or `false` for absent) |
| Anything-but | `{"anything-but": ["dev"]}` | Field is anything except listed values |

Combining: EventBridge matches ALL specified fields (AND). For OR
within a field, use a list.

## Target type comparison

| Target | Sync/Async | Default retry | Required permission |
|---|---|---|---|
| **Lambda** | Async | 185 attempts / 6h | `lambda:InvokeFunction` for `events.amazonaws.com` |
| **Step Functions** | Async | 185 attempts / 24h | `states:StartExecution` for `events.amazonaws.com` |
| **SQS** | Async | 185 attempts / 6h | `sqs:SendMessage` for `events.amazonaws.com` |
| **SNS** | Async | 185 attempts / 6h | `sns:Publish` for `events.amazonaws.com` |
| **ECS task** | Async | 185 attempts / 6h | `ecs:RunTask` for `events.amazonaws.com` |
| **Systems Manager** | Async | 185 attempts / 6h | `ssm:StartAutomationExecution` |
| **Batch** | Async | 185 attempts / 6h | `batch:SubmitJob` |
| **API destination** | Async | 3 attempts / 24h | Connection (OAuth/API key/basic) |
| **API Gateway** | Async | 185 attempts / 6h | `apigateway:POST` |
| **Redshift Data API** | Async | 185 attempts / 6h | `redshift-data:ExecuteStatement` |
| **Kinesis Firehose** | Async | 185 attempts / 6h | `firehose:PutRecord` |
| **SageMaker Pipeline** | Async | 185 attempts / 6h | `sagemaker:StartPipelineExecution` |

For ALL target types: ALWAYS configure explicit `RetryPolicy` and
`DeadLetterConfig`. Defaults are usually too aggressive.

## Retry policy semantics

| Field | Meaning | Default |
|---|---|---|
| `MaximumRetryAttempts` | Total retries after initial attempt | 185 (most); 3 for API destinations |
| `MaximumEventAgeInSeconds` | Max age of event for retry | 86400 (24h) |

Exponential backoff with jitter. First retry within seconds;
subsequent retries grow to minutes then hours. The retry window is
bounded by `MaximumEventAgeInSeconds`.

Tuning by workload:

| Workload | RetryAttempts | EventAge | Rationale |
|---|---|---|---|
| User-facing notification (Slack, email) | 3 | 900s (15m) | A 24h-old notification is worse than none |
| Compliance audit (must not lose) | 185 (default) | 86400s | Persistence over latency |
| API destination with rate-limited endpoint | 5 | 3600s | Allow backoff but bound it |
| Step Functions long-running workflow | 2 | 86400s | SFN handles its own internal retries |
| Lambda with idempotent consumer | 5 | 3600s | Trust idempotency; bound the retry storm |

## DLQ wiring

DLQ is per-target via `DeadLetterConfig.arn`. The DLQ MUST be an SQS
queue (not SNS, not Kinesis). EventBridge delivers the original
event envelope to the DLQ after exhausting retries.

```bash
aws sqs create-queue --queue-name eventbridge-<rule>-dlq
aws sqs set-queue-attributes \
  --queue-url https://sqs.<region>.amazonaws.com/<account>/eventbridge-<rule>-dlq \
  --attributes MessageRetentionPeriod=1209600
aws events put-targets --rule <rule> --event-bus-name <bus> \
  --targets '[{"Id":"<id>","Arn":"<target-arn>","DeadLetterConfig":{"Arn":"arn:aws:sqs:<region>:<account>:eventbridge-<rule>-dlq"},"RetryPolicy":{"MaximumRetryAttempts":3,"MaximumEventAgeInSeconds":900}}]'
```

Always set SQS retention to 14 days (1209600s) max to give operators
time to triage. Default 4 days is too short.

## Input transformer patterns

`InputTransformer` has two parts:
- `InputPathsMap`: JSONPath strings extracting values from the event
- `InputTemplate`: JSON or string template referencing the paths

```json
{
  "InputPathsMap": {
    "user": "$.detail.user",
    "event_time": "$.time",
    "source": "$.source"
  },
  "InputTemplate": "{\"event_type\":\"eventbridge-trigger\",\"user\":<user>,\"triggered_at\":\"<event_time>\",\"origin\":\"<source>\"}"
}
```

Rules:
- `InputPathsMap` values are JSONPath strings starting with `$.`
- `<placeholder>` in `InputTemplate` references `InputPathsMap` keys
- For string JSON output, wrap placeholder in quotes: `"<user>"`
- For non-string (numbers, objects, arrays), use bare: `<value>`
- Without `InputTransformer`, target receives the FULL original event
  envelope (version, id, time, source, detail-type, detail, account,
  region)

## Lambda invocation permission

Required after `put-targets` for Lambda targets:

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

A missing or revoked permission produces silent non-delivery. The
error surfaces in CloudTrail as `AccessDenied` from
`events.amazonaws.com`, NOT in EventBridge metrics.

## Schedule expression formats

| Format | Example | Meaning |
|---|---|---|
| AWS cron (rules) | `cron(0 2 * * ? *)` | 02:00 UTC daily; `?` required in DOM or DOW |
| AWS cron (Scheduler) | `cron(0 2 * * *)` | Same; `?` optional |
| Rate | `rate(5 minutes)` | Every 5 minutes |
| Rate | `rate(1 hour)` | Every hour |
| Rate | `rate(1 day)` | Every day |

Cron field order: minutes, hours, day-of-month, month, day-of-week,
year. Value `?` means "no specific value" and is REQUIRED in either
DOM or DOW for rule syntax (mutually exclusive fields).

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
| Schedule rule never fires | Wrong cron syntax (both DOM and DOW set, no `?`) | Use `?` in one of DOM/DOW |
| Cross-account events not arriving | Bus policy missing `events:PutEvents` grant | `put-permission` on receiving bus |

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

## Bus policy templates

**Allow specific account:**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowAccount123456789012",
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
    "Action": "events:PutEvents",
    "Resource": "arn:aws:events:us-east-1:111111111111:event-bus/app-events",
    "Condition": {"StringEquals": {"aws:SourceAccount": "123456789012"}}
  }]
}
```

**Allow entire AWS Organization:**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowOrg",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "events:PutEvents",
    "Resource": "arn:aws:events:us-east-1:111111111111:event-bus/app-events",
    "Condition": {"StringEquals": {"aws:PrincipalOrgID": "o-xxxxxxxxxx"}}
  }]
}
```

**Allow a specific AWS service (e.g., CloudWatch alarm):**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowCloudWatchAlarms",
    "Effect": "Allow",
    "Principal": {"Service": "cloudwatch.amazonaws.com"},
    "Action": "events:PutEvents",
    "Resource": "arn:aws:events:us-east-1:111111111111:event-bus/app-events"
  }]
}
```
---

## Step 2: Event pattern operators (moved from SKILL.md)

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

## Step 3: Target type comparison (moved from SKILL.md)

| Target | Use | Pros | Cons |
|---|---|---|---|
| **Lambda** | Custom logic, lightweight transforms | Fast invocation; simple | 15-min timeout |
| **Step Functions** | Multi-step orchestration, long-running | State, retries, branching | Higher per-invocation cost |
| **SQS** | Decouple producer from consumer; buffering | Backpressure handling | Requires separate consumer |
| **SNS** | Fan-out to many subscribers | Many subscribers | Filter via SQS subs |
| **API destination** | External HTTP/S endpoint | Webhook delivery | Rate-limit, credential management |
| **ECS task** | Run a containerized job | Full runtime flexibility | Slower startup |
| **Systems Manager** | Run an Automation runbook | Native AWS ops integration | Async execution |
| **Batch** | Submitted job queue | Job scheduling, retries | Overkill for simple tasks |
| **Redshift Data API** | Run SQL on Redshift | Direct data warehouse access | Cluster availability dependency |
| **SageMaker Pipeline** | Trigger ML pipeline | Native ML orchestration | Pipeline execution cost |
| **API Gateway** | Trigger a REST endpoint | Existing API reuse | Auth surface |
| **Kinesis Firehose** | Stream to S3/Redshift/OpenSearch | Buffered delivery | Transformation limits |
| **Inspector** | Start an assessment run | Security automation | Async; assessment scope dep |

## Step 5: Input transformer common patterns (moved from SKILL.md)

Common patterns:

| Target type | Typical InputTemplate |
|---|---|
| Lambda | `{"event_type":"<name>", "payload": <detail>}` |
| Step Functions | `{"input": "{\"id\":\"<id>\",\"user\":\"<user>\"}"}` (escaped JSON string) |
| SQS | `{"body":"<detail>","type":"<source>"}` |
| API Destination | `{"event":"<name>","at":"<time>","detail":<detail>}` |

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
