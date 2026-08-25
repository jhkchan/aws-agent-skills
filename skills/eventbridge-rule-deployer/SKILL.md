---
name: eventbridge-rule-deployer
description: Provisions Amazon EventBridge rules and targets correctly the first time. Covers event-pattern rules (matching events from AWS services or custom sources) and schedule rules (cron/rate), content-based filtering (source, detail-type, detail JSON paths, exists, prefix, suffix, numeric, CIDR, anything-but), target wiring for Lambda, Step Functions, SQS, SNS, ECS, API Gateway, Kinesis, Redshift, SageMaker, and API Destinations, per-target DLQ and retry policy (MaximumRetryAttempts, MaximumEventAgeInSeconds), input transformation (InputPath, InputTemplate), cross-account bus policies, custom event-bus creation, archive and replay, EventBridge Scheduler vs scheduled rules, Pipes vs Rules, global endpoints, and Schema Registry. Emits READY_TO_DEPLOY with a working CLI plan or PREREQUISITES_MISSING with the specific gap. Use when provisioning rules, wiring targets with DLQ and retry, configuring input transformers, deploying cross-account routing, or setting up event archives.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan generation. Live deployment uses aws events put-rule, put-targets, put-events, test-event-pattern, create-event-bus, put-permission, create-archive, start-replay, describe-rule, list-targets-by-rule, aws lambda add-permission, aws scheduler create-schedule, and aws pipes create-pipe (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AppIntegration
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  when_to_use: Provisioning new EventBridge rules (event-pattern or schedule), wiring targets (Lambda, Step Functions, SQS, SNS, ECS, API Destination, API Gateway, Kinesis, Redshift, SageMaker), configuring per-target DLQ and retry policy, setting up input transformation, deploying cross-account event bus permissions, creating custom event buses, configuring archives for replay, or deciding between Scheduler, Pipes, and Rules for a workload.
  activation_triggers: create EventBridge rule, deploy EventBridge rule, EventBridge target Lambda, EventBridge scheduled rule, EventBridge cron, EventBridge rate expression, event pattern matching, EventBridge input transformer, EventBridge DLQ, retry policy EventBridge, cross-account event bus, custom event bus, EventBridge archive replay, EventBridge API destination, EventBridge Scheduler vs rules, EventBridge Pipes vs rules, global endpoints EventBridge, Schema Registry
  invocation_schema: 'Input: either (a) an event source and desired target ("trigger Lambda X when GuardDuty fires severity >= 7"), or (b) a schedule requirement ("run this Step Functions every night at 2am UTC"), or (c) a deployment plan request for an existing rule config. Output: deterministic PLAN block per rule — RULE/TARGETS/RETRY/ DLQ/INPUT_TRANSFORM/PREREQUISITES/VERDICT — where VERDICT is READY_TO_DEPLOY (CLI plan complete and pre-flight green) or PREREQUISITES_MISSING (specific gap cited).'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: EventBridge, event bus, event pattern, scheduled rule, cron rule, rate rule, rule targets, dead-letter queue, DLQ, retry policy, input transformer, InputTemplate, cross-account events, event bus policy, custom event bus, archive and replay, EventBridge Scheduler, EventBridge Pipes, global endpoints, Schema Registry, API destination, provision rules
  tags: eventbridge, app-integration, event-driven, deploy, rules, targets, dlq
---

# EventBridge Rule Deployer

## Mindset

**One-line takeaway:** an EventBridge rule is a **stateless filter
plus a fan-out dispatcher** — it matches events on a bus (or fires
on a schedule) and dispatches to up to 5 targets. Correct deployment
is three independent gates: pattern (does the right event match?),
target wiring (does the right consumer get invoked with the right
payload?), and resilience (DLQ + retry + idempotency). Skip any one
and the workflow is silently broken in production.

- **Pattern vs Schedule is the first fork.** A pattern rule listens
  on a bus for matching events; a schedule rule fires on a cron/rate.
  They share the `put-rule` API but share no semantics. Picking the
  wrong type produces a rule that never fires (schedule when events
  are expected) or fires on every event (pattern when a schedule is
  intended).
- **The target is where most production bugs live.** A mis-scoped
  invocation permission, a missing DLQ, an unconfigured input
  transformer, or a target ARN from the wrong account each produces
  silent non-delivery. The rule looks healthy; the consumer never
  runs.
- **At-least-once delivery is the implicit contract.** EventBridge
  may deliver the same event multiple times (retry, replay, regional
  failover). Every target consumer MUST be idempotent. A rule
  deployment that omits an idempotency note for the consumer is
  incomplete.

## Quick navigation

| You want to... | Go to |
|---|---|
| Pick pattern vs schedule rule | Step 1 |
| Write an event pattern (filtering) | Step 2 + Appendix A |
| Pick a target type | Step 3 |
| Wire retry policy and DLQ | Step 4 |
| Configure input transformation | Step 5 |
| Deploy cross-account event routing | Step 6 |
| Use custom event bus vs default | Step 7 |
| Configure archive and replay | Step 8 |
| Pick between Rules, Pipes, Scheduler | Step 9 |
| Configure global endpoints | Step 10 |
| Enable Schema Registry | Step 11 |
| Verify the deployment | Step 12 + Pre-flight |
| Avoid silent-delivery pitfalls | Anti-Patterns |
| Reduce a partial deployment to READY_TO_DEPLOY | Output format |

## Critical rules at a glance (do NOT bury these)

1. **Every target MUST have a DLQ.** EventBridge retries for up to
   24 hours; after exhaustion, the event is dropped silently unless
   `DeadLetterConfig` is set per target. A target without DLQ is
   silent data loss.
2. **Lambda targets need `lambda:AddPermission`.** EventBridge
   cannot invoke a Lambda without an explicit
   `lambda:InvokeFunction` grant for `events.amazonaws.com`. A
   missing permission is the most common silent non-delivery
   failure — the rule matches, the Lambda never runs.
3. **Pattern and InputTransformer are separate concerns.**
   `EventPattern` filters which events match. `InputTransformer`
   reshapes the matched event for the target. Filtering in the
   transformer is a silent no-op; transforming in the pattern is
   ignored.
4. **Default bus is for AWS-service events only.** Application
   events on the default bus mix with EC2/GuardDuty/Security Hub
   events and complicate access control, schema discovery, and
   retention. Use a custom bus for application events.
5. **Schedule rules are NOT EventBridge Scheduler.** Schedule rules
   (`put-rule --schedule-expression`) are the legacy path. Scheduler
   (`scheduler create-schedule`) is the modern path with per-schedule
   IAM roles, timezones, and one-time schedules. Prefer Scheduler for
   any new time-based workflow.

## Pre-flight: data requirements

| Input | Source | Why |
|---|---|---|
| Event source (for pattern rules) | Service docs / `events list-event-sources` | Drives the `source` field |
| Detail-type | Service docs | Drives the `detail-type` filter |
| Sample event payload | `PutEvents` test or `TestEventPattern` | Validates the pattern matches before deploy |
| Target type and ARN | Application config / `aws lambda list-functions` etc. | Determines target config |
| Region(s) | Single-region vs multi-region | Drives global-endpoint decision |
| Existing rules on the bus | `aws events list-rules --event-bus-name <bus>` | Detect name collisions and rule-graph cycles |
| Cross-account producer account IDs | `aws organizations list-accounts` or stated input | Required for bus policy |
| Existing DLQs | `aws sqs list-queues --queue-name-prefix eventbridge-` | Reuse vs create |

**If the input is malformed** (no event source for a pattern rule,
no target ARN, ambiguous bus), emit:

```text
PLAN: <reference>
RULE: <rule-name or "unknown">
VERDICT: PREREQUISITES_MISSING
GAP: Cannot generate deployment plan — required inputs missing.
     Re-supply: event source + detail-type (pattern rules) OR
     schedule expression (schedule rules), and at least one target
     ARN.
```

## Process — Deployment plan (apply in order)

### Step 0: Expert knowledge — non-obvious EventBridge behaviors

These behaviours change a deployment plan if ignored. Each has caused
production silent-non-delivery incidents:

- **`PutEvents` is the only event ingestion API.** AWS services call
  it implicitly; applications must call it explicitly. The bus
  policy controls who can call `PutEvents` — same-account same-bus
  is implicit, cross-account requires a resource policy.

- **`EventPattern` is JSONPath-like, not full JSONPath.** It supports
  exact match, prefix, suffix, contains, equals-ignore-case, numeric
  ranges, CIDR matching, exists, and anything-but. It does NOT
  support arbitrary JSONPath expressions like `$..user`. Complex
  filters must be done in the consumer.

- **`InputTransformer` is per-target and replaces the payload.** A
  rule can have up to 5 targets, each with its own transformer. The
  original event payload is NOT passed to the target unless the
  transformer explicitly maps it via `InputPathsMap` +
  `InputTemplate`.

- **`put-targets` accepts a non-existent DLQ ARN silently.** The
  first failed delivery will then fail to write to the DLQ — double
  silent failure. Always verify the DLQ exists with
  `aws sqs get-queue-url` before `put-targets`.

- **`test-event-pattern` is the deployment test fixture.** It
  validates a pattern against a sample event WITHOUT creating the
  rule. Always run it before `put-rule` to confirm the match.

- **Schedule expression format differs by AWS service.** EventBridge
  rules use AWS cron with required `?` in the day-of-week or
  day-of-month field (`cron(0 2 * * ? *)`). EventBridge Scheduler
  uses standard cron with optional `?`. Mixing them produces a
  validation error.

- **Same-bus same-account PutEvents does not require a bus policy.**
  Same-account access is implicit. The bus policy gates
  cross-account and service-principal delegation only.

- **Cross-account rules are bus-policy + target-ACL problems.** The
  producing account needs `events:PutEvents` permission on the
  receiving bus (via bus resource policy). The receiving rule's
  target must trust the producing account if it is in yet another
  account.

- **`PutEvents` accepts up to 10 events per call, 256 KB per event,
  2 MB total.** Events over 256 KB must be parked in S3 and
  referenced by URI in the event detail. Application publishers must
  batch and respect size caps.

- **API destinations rate-limit per connection.** A target API
  destination has a per-connection rate limit (default 300 TPS).
  Sustained excess is buffered up to the
  `InvocationRateLimitPerSec` cap; sustained overage is dropped to
  DLQ.

- **Archives replay to ALL matching rules — including rules created
  AFTER the original events.** Replay can cause unexpected duplicate
  processing. Pause new rules before replaying.

- **Rule quotas: 300 rules per bus, 5 targets per rule.** A
  high-volume workflow with many filtered sub-routes hits the cap.
  Fan out to SQS for finer-grained per-consumer filtering.

- **Scheduler has a 1M-schedule quota; rule-based scheduling has a
  300-rule-per-bus quota.** Beyond ~300 schedules, use Scheduler.

- **Global endpoints replicate EVENTS, not rules.** Both regional
  buses must have equivalent rules and targets. A failover to a bus
  without matching rules is silent event loss.

- **Schema Registry auto-discovery captures schemas only on the
  default bus by default.** Custom-bus schema discovery must be
  explicitly enabled via `discoverers` API.

### Step 1: Pick pattern vs schedule rule

```
Is the trigger an event on a bus?
├─ Yes → Event-pattern rule (put-rule --event-pattern)
│        ├─ AWS service event? → default bus
│        ├─ Application event? → custom bus (Step 7)
│        └─ Partner event? → partner bus / SaaS partner integration
└─ No  → Time-based?
        ├─ New workload → EventBridge Scheduler (Step 9) — preferred
        └─ Existing rule-based cron → Schedule rule (put-rule --schedule-expression)
```

**Pattern rule** — triggered by matching events:

```bash
aws events put-rule \
  --name guardduty-high-severity \
  --event-bus-name default \
  --event-pattern '{"source":["aws.guardduty"],"detail-type":["GuardDuty Finding"],"detail":{"severity":[{"numeric":[">=",7]}]}}' \
  --state ENABLED \
  --description "Match GuardDuty severity >= 7"
```

**Schedule rule** — cron-based (legacy path; prefer Scheduler):

```bash
aws events put-rule \
  --name nightly-backup \
  --schedule-expression 'cron(0 2 * * ? *)' \
  --state ENABLED \
  --description "Run nightly at 02:00 UTC"
```

**Rate rule** — fixed interval:

```bash
aws events put-rule \
  --name healthcheck-every-5-min \
  --schedule-expression 'rate(5 minutes)' \
  --state ENABLED
```

| Dimension | Pattern rule | Schedule rule |
|---|---|---|
| Trigger | Matching event on bus | Cron/rate expression |
| Source | `--event-pattern` JSON | `--schedule-expression` string |
| Use case | Event-driven automation | Time-based job |
| Modern alternative | n/a | EventBridge Scheduler (Step 9) |

### Step 2: Write the event pattern

Filter operators (Appendix A has the full table):

```json
{
  "source": ["aws.guardduty"],
  "detail-type": ["GuardDuty Finding"],
  "detail": {
    "severity": [{"numeric": [">=", 7]}],
    "service": {"action": {"networkConnectionAction": {"connectionDirection": ["IN"]}}}
  }
}
```

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

Validate before deploying:

```bash
aws events test-event-pattern \
  --event-pattern file://pattern.json \
  --event file://sample-event.json
```

A pattern that returns no matches on a real sample will never fire in
production. Always test.

### Step 3: Pick target type

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

Target wiring pattern:

```bash
aws events put-targets \
  --rule <rule-name> \
  --event-bus-name <bus> \
  --targets '[{"Id":"lambda-target","Arn":"arn:aws:lambda:us-east-1:111111111111:function:my-fn","DeadLetterConfig":{"Arn":"arn:aws:sqs:us-east-1:111111111111:eventbridge-my-rule-dlq"},"RetryPolicy":{"MaximumRetryAttempts":3,"MaximumEventAgeInSeconds":900}}]'
```

For Lambda targets, grant EventBridge permission to invoke:

```bash
aws lambda add-permission \
  --function-name my-fn \
  --statement-id EventBridgeInvoke-<rule-name> \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-1:111111111111:rule/<bus>/<rule-name> \
  --source-account 111111111111
```

A missing invocation permission produces silent non-delivery. Verify
after wiring:

```bash
aws lambda get-policy --function-name my-fn --query 'Policy' --output text \
  | jq '.Statement[] | select(.Principal.Service=="events.amazonaws.com")'
```

### Step 4: Wire retry policy and DLQ

Every target MUST have BOTH a retry policy and a DLQ. Defaults (185
retries, 24h max age) are usually too aggressive.

| Workload | RetryAttempts | EventAge | DLQ |
|---|---|---|---|
| Fast, transient failures (Lambda throttled) | 3 | 900s (15 min) | Yes |
| User-facing API destination | 5 | 3600s (1h) | Yes |
| Long-running Step Functions workflow | 2 | 86400s (24h) | Yes |
| Compliance audit (must not lose) | 185 (default) | 86400s | Yes |

Create the DLQ first, then attach:

```bash
aws sqs create-queue --queue-name eventbridge-<rule>-dlq
aws sqs set-queue-attributes \
  --queue-url https://sqs.<region>.amazonaws.com/<account>/eventbridge-<rule>-dlq \
  --attributes MessageRetentionPeriod=1209600
aws events put-targets \
  --rule <rule> --event-bus-name <bus> \
  --targets '[{"Id":"<target-id>","Arn":"<target-arn>","DeadLetterConfig":{"Arn":"arn:aws:sqs:<region>:<account>:eventbridge-<rule>-dlq"},"RetryPolicy":{"MaximumRetryAttempts":3,"MaximumEventAgeInSeconds":900}}]'
```

CloudWatch alarm on DLQ depth (non-negotiable for production):

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name EventBridge-<rule>-DLQ-Depth \
  --metric-name ApproximateNumberOfMessagesVisible \
  --namespace AWS/SQS \
  --statistic Sum --period 60 --evaluation-periods 1 \
  --threshold 0 --comparison-operator GreaterThanThreshold \
  --dimensions Name=QueueName,Values=eventbridge-<rule>-dlq \
  --alarm-actions <sns-arn>
```

### Step 5: Configure input transformation

`InputTransformer` reshapes the matched event for the target. Two
parts: `InputPathsMap` (extract values from the event) and
`InputTemplate` (build the new payload).

```bash
aws events put-targets \
  --rule <rule> --event-bus-name <bus> \
  --targets '[{
    "Id":"lambda-target",
    "Arn":"arn:aws:lambda:us-east-1:111111111111:function:my-fn",
    "InputTransformer":{
      "InputPathsMap":{
        "user":"$.detail.user",
        "event_time":"$.time",
        "source":"$.source"
      },
      "InputTemplate":"{\"event_type\":\"eventbridge-trigger\",\"user\":<user>,\"triggered_at\":\"<event_time>\",\"origin\":\"<source>\"}"
    }
  }]'
```

Key rules:
- `InputPathsMap` values are JSONPath strings starting with `$.`
- `<placeholder>` in `InputTemplate` references `InputPathsMap` keys
- For string values in JSON output, wrap placeholder in quotes: `"<user>"`
- For non-string values (numbers, objects, arrays), use bare: `<value>`
- A target without an `InputTransformer` receives the **full original
  event envelope** (including `version`, `id`, `time`, `source`,
  `detail-type`, `detail`, `account`, `region`)

Common patterns:

| Target type | Typical InputTemplate |
|---|---|
| Lambda | `{"event_type":"<name>", "payload": <detail>}` |
| Step Functions | `{"input": "{\"id\":\"<id>\",\"user\":\"<user>\"}"}` (escaped JSON string) |
| SQS | `{"body":"<detail>","type":"<source>"}` |
| API Destination | `{"event":"<name>","at":"<time>","detail":<detail>}` |

### Step 6: Deploy cross-account event routing

Cross-account events require TWO configurations:

1. **Receiving bus resource policy** grants the producing account
   `events:PutEvents` permission:

```bash
aws events put-permission \
  --event-bus-name <receiving-bus> \
  --action events:PutEvents \
  --principal <producer-account-id> \
  --statement-id AllowProducerAccount-<id> \
  --condition '{"Type":"StringEquals","Key":"aws:SourceAccount","Value":"<producer-account-id>"}'
```

2. **Producer calls PutEvents with the receiving bus ARN:**

```bash
aws events put-events \
  --entries '[{"EventBusName":"arn:aws:events:us-east-1:<receiver-account>:event-bus/<receiving-bus>","Source":"my.app","DetailType":"order.created","Detail":"{\"order_id\":\"ord-123\"}"}]'
```

For organization-wide routing (all accounts in an Organization):

```bash
aws events put-permission \
  --event-bus-name <receiving-bus> \
  --action events:PutEvents \
  --principal "*" \
  --statement-id AllowOrg \
  --condition '{"Type":"StringEquals","Key":"aws:PrincipalOrgID","Value":"o-xxxxxxxxxx"}'
```

**Cross-account security rule:** prefer `aws:SourceAccount` or
`aws:PrincipalOrgID` over `aws:SourceIp` — IP-based restrictions are
bypassable.

### Step 7: Use custom event bus vs default

| Bus type | Use when | Example events |
|---|---|---|
| **default** | AWS service events | `aws.ec2`, `aws.guardduty`, `aws.securityhub` |
| **custom** | Application events | `my.app.order`, `my.app.user` |
| **partner** | SaaS partner events | `aws.partner/datadog.com/*`, `aws.partner/stripe.com/*` |

Create a custom bus:

```bash
aws events create-event-bus \
  --name app-events \
  --event-source-name "" \
  --tags '[{"Key":"Owner","Value":"app-team"},{"Key":"Environment","Value":"prod"}]'
```

Naming conventions:
- Lowercase, hyphen-separated: `app-events`, `order-bus`, `audit-events`
- Avoid `default` (reserved), `aws.*` (reserved for AWS)
- Prefix with team or domain for clarity: `payments-events`, `secops-events`

Cross-bus routing is not supported — a rule on the default bus
cannot match events on a custom bus. Use a Lambda on the default bus
that re-publishes to the custom bus if cross-bus routing is required.

### Step 8: Configure archive and replay

Archives capture events for debugging and replay. Create on a bus:

```bash
aws events create-archive \
  --name app-events-archive \
  --event-source-arn arn:aws:events:us-east-1:111111111111:event-bus/app-events \
  --retention 7 \
  --event-pattern '{"source":["my.app"]}'
```

Replay a specific time range:

```bash
aws events start-replay \
  --name debug-2026-08-incident \
  --event-source-arn arn:aws:events:us-east-1:111111111111:event-bus/app-events \
  --event-start-time 2026-08-04T00:00:00Z \
  --event-end-time 2026-08-04T06:00:00Z \
  --destination '{"Arn":"arn:aws:events:us-east-1:111111111111:event-bus/app-events"}'
```

**Critical warnings:**
- Replay re-publishes events to ALL rules matching the archive
  pattern, including rules created AFTER the original events. Pause
  new rules before replaying.
- Archives are NOT backups — they are operational tools. For
  compliance retention, use S3 with lifecycle policies.
- Archives bill per-event-month. A high-volume bus with 90-day
  retention is a significant line item. Default to 7-30 days.

### Step 9: Pick between Rules, Pipes, Scheduler

```
Is the source a stream or queue (DynamoDB Streams, Kinesis, SQS, MQ)?
├─ Yes → EventBridge Pipes (create-pipe)
└─ No  → Is the trigger time-based (cron/rate)?
        ├─ Yes → EventBridge Scheduler (create-schedule) for new work
        │         OR schedule rule (put-rule --schedule-expression) for legacy
        └─ No  → EventBridge rule (put-rule --event-pattern)
```

| Dimension | Rule | Pipes | Scheduler |
|---|---|---|---|
| Source | Event bus | DynamoDB Streams / Kinesis / SQS / MQ / MSK | Time-based |
| Filtering | EventPattern | FilterCriteria | n/a |
| Enrichment | InputTransformer | Lambda / SFN / API destination in-between | n/a |
| Per-schedule management | n/a | n/a | First-class resource |
| Quota | 300 rules per bus | 200 pipes per region (soft) | 1M schedules per account |
| Use case | Service event routing | Stream/queue fan-out | Time-based triggers |

For any new time-based workflow, default to Scheduler unless event-
pattern matching is required.

### Step 10: Configure global endpoints

For multi-region failover:

```bash
aws events create-endpoint \
  --name orders-failover \
  --routing-config '{"FailoverConfig":{"Primary":{"HealthCheck":"arn:aws:route53:...:healthcheck/primary"},"Secondary":{"RouteDetails":{"HealthCheck":"arn:aws:route53:...:healthcheck/secondary"}}}}' \
  --event-buses '[{"EventBusArn":"arn:aws:events:us-east-1:111111111111:event-bus/orders"},{"EventBusArn":"arn:aws:events:us-west-2:111111111111:event-bus/orders"}]' \
  --replication-config '{"State":"ENABLED"}'
```

Requirements:
- Both buses must have equivalent rules and targets
- Both buses must have equivalent bus policies, DLQs, KMS keys
- Schema Registry and archives are per-region — replicate separately
- Producers target the endpoint ARN, not a regional bus ARN
- Failover is driven by Route53 health checks; replication is
  asynchronous (a few seconds of lag during failover)

### Step 11: Enable Schema Registry

```bash
aws schemas create-registry \
  --registry-name app-events-schemas \
  --description "Discovered schemas for app-events bus"

aws schemas create-discoverer \
  --discoverer-name app-events-discoverer \
  --source-arn arn:aws:events:us-east-1:111111111111:event-bus/app-events \
  --description "Auto-discover schemas from app-events bus"
```

Notes:
- Auto-discovery captures schemas ONLY on the default bus by default
- Custom-bus schema discovery must be explicitly enabled via
  `create-discoverer`
- Code bindings (Java, Python, TypeScript) can be generated from
  discovered schemas for type-safe event publishing/consumption
- Do NOT enable schema discovery on a bus with untrusted publishers —
  attacker-crafted events pollute the registry

### Step 12: Verify the deployment

```bash
# 1. Rule exists and is ENABLED
aws events describe-rule --name <rule> --event-bus-name <bus> \
  --query '[Name, State, EventPattern, ScheduleExpression]'

# 2. Targets wired with DLQ and retry
aws events list-targets-by-rule --rule <rule> --event-bus-name <bus>

# 3. Lambda invocation permission
aws lambda get-policy --function-name <fn> --query 'Policy' --output text \
  | jq '.Statement[] | select(.Principal.Service=="events.amazonaws.com")'

# 4. DLQ exists and depth is zero
aws sqs get-queue-url --queue-name eventbridge-<rule>-dlq
aws sqs get-queue-attributes \
  --queue-url https://sqs.<region>.amazonaws.com/<account>/eventbridge-<rule>-dlq \
  --attribute-names ApproximateNumberOfMessagesVisible

# 5. Bus policy for cross-account (if applicable)
aws events describe-event-bus --name <bus> --query 'Policy'

# 6. Archive configured (if used)
aws events describe-archive --archive-name <archive>

# 7. Test the pattern against a fresh sample
aws events test-event-pattern \
  --event-pattern file://pattern.json --event file://sample-event.json

# 8. CloudWatch metrics post-deploy
aws cloudwatch get-metric-statistics \
  --namespace AWS/Events \
  --metric-name Invocations \
  --dimensions Name=RuleName,Values=<rule> \
  --start-time $(date -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date +%Y-%m-%dT%H:%M:%S) --period 300 --statistics Sum

# 9. TriggeredInvocations vs FailedInvocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Events \
  --metric-name FailedInvocations \
  --dimensions Name=RuleName,Values=<rule> \
  --start-time $(date -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date +%Y-%m-%dT%H:%M:%S) --period 300 --statistics Sum
```

## Output format

```text
PLAN: <reference>
RULE:
  Name: <rule-name>
  Bus: <bus-name>
  Type: event-pattern | schedule
  Pattern: <pattern summary>
  Schedule: <cron/rate if schedule rule>
  State: ENABLED
TARGETS:
  - <target-id> (<target-type>): <target-arn>
    RetryPolicy: <attempts> / <max-age>
    DeadLetterConfig: <dlq-arn>
    InputTransformer: <yes — describe map | no — full event>
    InvocationPermission: <verified | pending>
RETRY: <policy summary>
DLQ: <dlq-arn with retention>
INPUT_TRANSFORM: <map summary or "full event">
CROSS_ACCOUNT: <none | bus policy + target ACL summary>
ARCHIVE: <none | archive-name with retention>
PREREQUISITES:
  [x] Pattern validated via TestEventPattern
  [x] Targets exist and ARNs verified
  [x] DLQs exist with 14-day retention
  [x] Lambda invocation permissions granted
  [x] Bus policy attached (cross-account only)
  [x] CloudWatch alarm on DLQ depth
  [x] Idempotency note for consumer
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
GAP: <if PREREQUISITES_MISSING, the specific missing item(s)>
TEMPLATE: <CLI snippet for put-rule + put-targets + add-permission>
```

### Worked example — READY_TO_DEPLOY, GuardDuty to Lambda

```text
PLAN: guardduty-remediation-deploy
RULE:
  Name: guardduty-high-severity
  Bus: default
  Type: event-pattern
  Pattern: source=aws.guardduty, detail-type=GuardDuty Finding, detail.severity>=7
  State: ENABLED
TARGETS:
  - isolate-instance (Lambda): arn:aws:lambda:us-east-1:111111111111:function:isolate-instance
    RetryPolicy: 3 attempts / 900s max age (fail-fast for security)
    DeadLetterConfig: arn:aws:sqs:us-east-1:111111111111:eventbridge-guardduty-high-severity-dlq
    InputTransformer: no (Lambda handles full event)
    InvocationPermission: verified
RETRY: 3 attempts / 15 min
DLQ: eventbridge-guardduty-high-severity-dlq (14-day retention)
INPUT_TRANSFORM: full event
CROSS_ACCOUNT: none
ARCHIVE: none (compliance archive recommended)
PREREQUISITES:
  [x] Pattern validated via TestEventPattern
  [x] Targets exist and ARNs verified
  [x] DLQ exists with 14-day retention
  [x] Lambda invocation permission granted
  [x] CloudWatch alarm on DLQ depth configured
  [x] Idempotency note: consumer dedupes on detail.id (finding ID)
VERDICT: READY_TO_DEPLOY
GAP: None
TEMPLATE:
  aws events put-rule --name guardduty-high-severity --event-bus-name default --event-pattern '{"source":["aws.guardduty"],"detail-type":["GuardDuty Finding"],"detail":{"severity":[{"numeric":[">=",7]}]}}' --state ENABLED
  aws sqs create-queue --queue-name eventbridge-guardduty-high-severity-dlq
  aws sqs set-queue-attributes --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/eventbridge-guardduty-high-severity-dlq --attributes MessageRetentionPeriod=1209600
  aws events put-targets --rule guardduty-high-severity --event-bus-name default --targets '[{"Id":"isolate-instance","Arn":"arn:aws:lambda:us-east-1:111111111111:function:isolate-instance","DeadLetterConfig":{"Arn":"arn:aws:sqs:us-east-1:111111111111:eventbridge-guardduty-high-severity-dlq"},"RetryPolicy":{"MaximumRetryAttempts":3,"MaximumEventAgeInSeconds":900}}]'
  aws lambda add-permission --function-name isolate-instance --statement-id EventBridgeInvoke-guardduty-high-severity --action lambda:InvokeFunction --principal events.amazonaws.com --source-arn arn:aws:events:us-east-1:111111111111:rule/default/guardduty-high-severity --source-account 111111111111
```

### Worked example — PREREQUISITES_MISSING, no DLQ

```text
PLAN: codebuild-notify-deploy
RULE:
  Name: codebuild-failed
  Bus: default
  Type: event-pattern
  Pattern: source=aws.codebuild, detail-type=CodeBuild Build State Change, detail.build-status=FAILED
  State: ENABLED
TARGETS:
  - notify-slack (Lambda): arn:aws:lambda:us-east-1:111111111111:function:notify-slack
    RetryPolicy: defaults (185 attempts / 24h) — too aggressive for notification
    DeadLetterConfig: NONE
    InputTransformer: no
    InvocationPermission: verified
RETRY: defaults (185 / 24h) — should be 3 / 900s
DLQ: NONE — silent event loss on Lambda failure
INPUT_TRANSFORM: full event
CROSS_ACCOUNT: none
PREREQUISITES:
  [x] Pattern validated via TestEventPattern
  [x] Target exists and ARN verified
  [ ] DLQ missing — create eventbridge-codebuild-failed-dlq
  [x] Lambda invocation permission verified
  [ ] CloudWatch alarm on DLQ depth not configured
  [ ] Idempotency note missing — CodeBuild emits multiple state-change events per build
VERDICT: PREREQUISITES_MISSING
GAP: (1) DLQ not configured — failed invocations will be silently dropped after retry exhaustion. (2) Default retry policy (185 attempts / 24h) is too aggressive for a Slack notification; should be 3 attempts / 900s. (3) No idempotency note — CodeBuild emits multiple state-change events per build (STARTED, IN_PROGRESS, FAILED, FAILED-retry); the Lambda will post duplicate Slack messages without dedup on detail.build-id + detail.build-status. (4) No CloudWatch alarm on DLQ depth. Address all four before deployment.
TEMPLATE: (incomplete — fix GAPs first)
```

## Anti-Patterns — NEVER do these things

- NEVER ship a target without a DLQ. EventBridge drops events
  silently after the retry window. A target without
  `DeadLetterConfig` is silent data loss.

- NEVER assume single-delivery. EventBridge is at-least-once.
  Consumers MUST be idempotent — duplicate notifications, duplicate
  charges, duplicate resource creation are all expected production
  behaviour without dedup.

- NEVER use the default bus for application events. The default bus
  receives AWS service events. Mixing application events with
  service events complicates routing, access control, and schema
  discovery. Use a custom bus.

- NEVER confuse `EventPattern` with `InputTransformer`.
  `EventPattern` filters which events match. `InputTransformer`
  reshapes the matched event for the target. Trying to filter in
  the transformer (or transform in the pattern) is a silent no-op.

- NEVER use `aws:SourceIp` as the sole condition for cross-account
  `PutEvents`. IP-based restrictions are bypassable. Use
  `aws:SourceAccount` or `aws:PrincipalOrgID`.

- NEVER assume rule ENABLED means targets receive events. A rule
  can be ENABLED with zero targets, or targets without invocation
  permissions. Always verify with `list-targets-by-rule` and a
  sample `TestEventPattern`.

- NEVER assume event ordering across rules. EventBridge does not
  guarantee delivery order across rules on the same bus. If order
  matters (e.g., create-then-update), serialize via SQS FIFO or
  Step Functions.

- NEVER use EventBridge cron rules for new time-based workflows
  when EventBridge Scheduler is available. Scheduler gives
  per-schedule management, timezone support, start/end windows, and
  one-time schedules.

- NEVER forget the Lambda invocation permission. A target without
  `lambda:AddPermission` for `events.amazonaws.com` produces silent
  non-delivery. The rule matches; the Lambda never runs.

- NEVER use `PutEvents` to deliver payloads over 256 KB. The API
  rejects them. Park large payloads in S3 and reference by URI in
  the event detail.

- NEVER assume `put-targets` validates the DLQ ARN. A non-existent
  DLQ ARN is accepted silently; the first failed delivery then
  fails to write to the DLQ — double silent failure. Always verify
  the DLQ exists first.

- NEVER archive events on a high-volume bus without a retention
  cap. Archives bill per-event-month. A 1M events/day bus with
  90-day retention is 90M event-months. Default to 7-30 days for
  operational replay.

- NEVER enable schema discovery on a bus that receives untrusted
  publisher events. Schema discovery captures event shapes;
  attacker-crafted events pollute the registry.

- NEVER assume a global endpoint replicates rules. Global endpoints
  replicate EVENTS between regional buses. Rules are regional —
  both regions must have equivalent rule configurations. A global
  endpoint without matching rules on the secondary bus fails
  silently during failover.

- NEVER deliver to an API destination without monitoring
  `InvocationHttpStatusCode`. A revoked OAuth credential or rotated
  API key produces silent delivery failure until the DLQ fills.

- NEVER use a cron expression with both day-of-month and day-of-week
  set in an EventBridge rule (rule syntax requires `?` in one of
  them). The rule creation will fail validation.

## Pre-flight safety checks (run before applying any deploy CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing
  operation (`put-rule`, `put-targets`, `put-permission`,
  `create-event-bus`, `create-archive`, `start-replay`,
  `create-endpoint`), emit:
  `CONFIRM: About to <action> on bus <bus> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`

- **Test the pattern first.** Before `put-rule`, run
  `test-event-pattern` against a known-good sample event. A pattern
  that returns no matches in test will never fire in production.

- **Verify the DLQ exists** before `put-targets`. Run
  `aws sqs get-queue-url --queue-name eventbridge-<rule>-dlq`. A
  non-existent DLQ ARN is accepted silently and produces double
  silent failure on the first error.

- **Verify the Lambda invocation permission** after `put-targets`:
  `aws lambda get-policy --function-name <fn> --query 'Policy'`. A
  missing `events.amazonaws.com` principal is the most common
  silent failure.

- **Verify the target ARN region matches the bus region.** A
  cross-region target ARN in `put-targets` produces silent
  non-delivery. Use a global endpoint for cross-region delivery.

- **For cross-account rules**, verify the producing account has
  `events:PutEvents` on the receiving bus via bus policy. Test with
  a sample `PutEvents` from the producer before going live.

- **For global endpoints**, verify both regional buses have
  equivalent rules and targets. A failover to a bus without
  matching rules is silent event loss.

- **Map the rule graph** before adding a new rule that triggers a
  publishing Lambda. Detect cycles. A circular dependency cascades
  silently.

## Appendix A — Event pattern operators

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

## Appendix B — Common AWS event sources

| Source | Detail-type | Common filter | Typical target |
|---|---|---|---|
| `aws.ec2` | `EC2 Instance State-change Notification` | `detail.state=["running"]` | Lambda auto-tagger |
| `aws.guardduty` | `GuardDuty Finding` | `detail.severity>=7` | Lambda isolate-instance |
| `aws.securityhub` | `Security Hub Findings - Imported` | `detail.findings[].Severity.Label=["CRITICAL","HIGH"]` | Step Functions workflow |
| `aws.codebuild` | `CodeBuild Build State Change` | `detail.build-status=["FAILED"]` | SNS + Lambda notify |
| `aws.autoscaling` | `EC2 Instance Launch Successful` | — | Lambda register-to-target-group |
| `aws.s3` | `Object Created` | `detail.object.key=[{"prefix":"uploads/"}]` | Lambda trigger-processing |
| `aws.cloudwatch` | `CloudWatch Alarm State Transition` | `detail.stateName=["ALARM"]` | SNS then Lambda ack |
| `aws.signin` | `AWS Console Sign In` | `detail.eventName=["ConsoleLogin"]`, `detail.responseElements.ConsoleLogin=["Success"]` | Lambda alert on new MFA-disabled logins |
| `aws.iam` | `AWS API Call via CloudTrail` | `detail.eventName=["DeleteRole"]` | Lambda revert or alert |
| `aws.health` | `AWS Health Event` | `detail.service=["EC2"]` | SNS page on-call |

## Appendix C — Decision tree (which architecture to deploy)

```
Is the source an AWS service event?
├─ Yes → Use the default bus.
│        └─ Is it a stream/queue source (DynamoDB Streams, Kinesis, SQS, MQ)?
│           ├─ Yes → Use EventBridge Pipes (Step 9).
│           └─ No  → Rule + target on default bus (Step 1-5).
└─ No  → Is it time-based (cron/rate)?
        ├─ Yes → EventBridge Scheduler (Step 9) for new work.
        └─ No  → Custom bus + rule + target (Step 7 + 1-5).

For rule + target deployments:
- Always attach DLQ (Step 4).
- Always note consumer idempotency (Step 5 critical-rule #2).
- Run the pre-flight safety checks before any state-changing CLI.
- For multi-region resilience, use global endpoints (Step 10).
```

## Expert heuristic: "The 5-point deployment gate"

Before emitting READY_TO_DEPLOY, every rule deployment plan MUST pass
these five checks. Any failure is PREREQUISITES_MISSING with a
specific citation:

1. **Pattern validates** — `test-event-pattern` returns a match on
   a known-good sample. A pattern that matches nothing in test will
   never fire in production.
2. **Target ARNs resolve** — every target ARN exists in the target
   account/region. A non-existent target produces silent non-delivery.
3. **DLQ exists with 14-day retention** — `aws sqs get-queue-url`
   returns the queue; `MessageRetentionPeriod=1209600`. Default 4-day
   retention is too short for triage.
4. **Invocation permissions granted** — Lambda targets have
   `events.amazonaws.com` in their resource policy; cross-account
   targets have the appropriate bus policy.
5. **Consumer idempotency noted** — the plan explicitly documents
   the dedup key (e.g., `detail.id`, `bucket+key+etag`,
   `build-id+status`) and the consumer's idempotency mechanism.
   EventBridge is at-least-once; a consumer without idempotency is
   a production incident waiting to happen.

If all five pass, emit READY_TO_DEPLOY. Any miss is a specific GAP.

## Recent AWS features (2024-2026)

- **EventBridge global endpoints GA (2024):** Automatic regional
  failover for event buses. Requires matching rules and targets on
  the secondary bus; verify before failover.

- **EventBridge Scheduler (2024-2025):** First-class time-based
  scheduling with per-schedule IAM roles, timezones, and one-time
  schedules. Preferred over cron-style EventBridge rules for any
  new time-based workflow.

- **EventBridge Pipes enhancements (2024):** Added support for
  self-managed Kafka, MSK, and improved enrichment (Lambda, Step
  Functions, API destination, Batch, ECS). Pipes are the standard
  path for stream/queue fan-out.

- **Schema Registry updates (2024):** OpenAPI and JSON Schema
  support. Discover schemas on custom buses explicitly — auto-
  discovery only applies to the default bus. Code bindings available
  for Java, Python, TypeScript.

- **EventBridge API destinations improvements (2024-2025):**
  Enhanced credential management for OAuth client-credentials. API
  key and basic-auth credentials still do NOT auto-rotate — monitor
  `InvocationHttpStatusCode` for stale credentials.

- **`PutEvents` batch size and EntrySize limits (2024):** Still 10
  entries per call, 256 KB per entry. Events over 256 KB must be
  parked in S3 and referenced by URI.

- **Cross-account event routing via AWS Organizations (2024):** Bus
  policies now support `aws:PrincipalOrgID` condition for
  organization-wide event routing. Simplifies multi-account
  architectures vs. enumerating each account principal.

## Domain

AWS CloudOps / App Integration — EventBridge Rule Provisioning.

## AWS documentation

- **Amazon EventBridge User Guide** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-what-is.html
- **EventBridge Rules** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rules.html
- **EventBridge Event Patterns** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html
- **EventBridge Targets** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-targets.html
- **EventBridge Input Transformation** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-transform-target-input.html
- **EventBridge Scheduler** — https://docs.aws.amazon.com/scheduler/latest/UserGuide/what-is-scheduler.html
- **EventBridge Pipes** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-pipes.html
- **EventBridge Global Endpoints** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-global-endpoints.html
- **EventBridge Schema Registry** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html
- **EventBridge Archive and Replay** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-archive.html
