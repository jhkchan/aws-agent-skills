---
name: event-driven-automator
description: 'Designs and implements event-driven architectures on Amazon EventBridge. Covers event bus selection (default, custom, partner), event pattern matching with content-based filtering, rule-to-target wiring (Lambda, Step Functions, SQS, SNS, API Gateway, API destinations, ECS, Systems Manager), EventBridge Pipes (DynamoDB Streams / Kinesis / SQS / MQ source with enrichment), and EventBridge Scheduler for time-based triggers. Adds the non-negotiables: per-target DLQ, idempotent consumers, retry policy, ordering semantics, circular-dependency detection, and dead-letter alarms. Covers common AWS event patterns (EC2 state change, GuardDuty finding, Security Hub finding, CodeBuild failure, Auto Scaling launch, S3 object created, CloudWatch alarm). Emits AUTOMATED with an architecture template or MANUAL_STEP_REQUIRED with the specific gap. Use when building EventBridge event-driven automation, designing Pipes pipelines, configuring Scheduler, or hardening event delivery with DLQ and idempotency.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline architecture design. Live deployment uses aws events create-event-bus, put-rule, put-targets, create-archive, update-event-bus, put-event (TestEventPattern), aws pipes create-pipe, start-pipe, aws scheduler create-schedule, get-schedule, and aws schemas create-registry (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AppIntegration
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: AUTOMATED | MANUAL_STEP_REQUIRED
  when_to_use: Designing an event-driven architecture on EventBridge, wiring rules to targets (Lambda, Step Functions, SQS, ECS, API destinations), building a Pipes pipeline from a stream/queue, configuring Scheduler for time-based triggers, hardening event delivery with DLQ and idempotency, or diagnosing event-matching and delivery failures.
  activation_triggers: EventBridge rule target, event-driven architecture, EventBridge Pipes, EventBridge Scheduler, event pattern matching, DLQ for events, idempotent consumer, GuardDuty finding automation, Security Hub finding workflow, CodeBuild failure notification, EC2 state change trigger, S3 object created trigger, circular dependency EventBridge, API destination, global endpoints EventBridge
  invocation_schema: 'Input: either (a) an event source and desired action ("when a GuardDuty finding arrives, run a Lambda to isolate the EC2 instance"), OR (b) an existing EventBridge rule/target configuration for review. Output: deterministic ARCHITECTURE block per workflow — BUS/PATTERN/TARGETS/RETRY/SAFETY/AUDIT/ VERDICT — where VERDICT is AUTOMATED (template ready) or MANUAL_STEP_REQUIRED (specific gap cited).'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: EventBridge, event bus, event pattern, rule targets, EventBridge Pipes, EventBridge Scheduler, DLQ, idempotency, retry policy, circular dependency, GuardDuty finding, Security Hub finding, CodeBuild failure, EC2 state change, Auto Scaling launch, S3 object created, CloudWatch alarm, API destination, Schema Registry, global endpoints, event-driven architecture
  tags: eventbridge, app-integration, event-driven, pipes, scheduler, automate
---

# Event-Driven Automator

## Mindset

Mindset prose (one-line takeaway, routing vs execution layer, at-least-once, per-partition ordering) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand framing an EventBridge design or explaining duplicate-delivery and ordering semantics.

## Quick navigation

| You want to... | Go to |
|---|---|
| Pick the right event bus | Step 1 |
| Write an event pattern (matching, content filtering) | Step 2 + Appendix A |
| Choose a target type (Lambda, SFN, SQS, ECS, API destination) | Step 3 |
| Configure retry policy and DLQ | Step 4 |
| Add idempotency to a consumer | Step 5 |
| Detect and break a circular dependency | Step 6 |
| Use EventBridge Pipes (stream/queue source) | Step 7 |
| Use EventBridge Scheduler (cron/rate) | Step 8 |
| Multi-region failover via global endpoints | Step 9 |
| Audit delivery, replay, and schema discovery | Step 10 |
| Common AWS event patterns (GuardDuty, CodeBuild, etc.) | Appendix B |
| Avoid delivery/idempotency pitfalls | Anti-Patterns |

## Critical rules at a glance (do NOT bury these)

1. **Every target MUST have a DLQ.** EventBridge retries for 6 hours
   (Lambda/SQS/SNS/ECS/SFN) or up to 24 hours (API destinations, with
   `MaximumEventAgeInSeconds`). After exhaustion, the event is dropped
   silently unless a DLQ is configured per-target via
   `DeadLetterConfig`. A target without DLQ is silent data loss.
2. **At-least-once delivery is not negotiable.** EventBridge may
   deliver the same event multiple times (retry, replay, regional
   failover). Consumers MUST be idempotent. A consumer that processes
   duplicate events (double-billing, double-notification, duplicate
   resource creation) is the most common production bug.
3. **Event patterns filter; they do not transform.** A rule
   `EventPattern` selects which events to route. Input transformation
   (`InputTransformer`) reshapes the payload for the target. These
   are separate concerns — confusing them produces events that match
   but the target receives the wrong shape.
4. **The default bus is for AWS-service events.** Custom application
   events should go to a custom bus. Putting application events on
   the default bus mixes them with EC2/GuardDuty/Security Hub events
   and complicates routing and access control.
5. **Circular dependencies cascade silently.** If rule A triggers
   Lambda B which publishes an event matching rule C which calls
   Lambda D which publishes an event matching rule A, the loop runs
   until a quota is hit or a target fails. Detect with a topology
   review before wiring.

## Pre-flight: data requirements

| Input | Source | Why |
|---|---|---|
| Event source + detail-type | `events list-event-sources` or known service docs | Drives the rule pattern |
| Sample event payload | `aws events test-event-pattern` or `PutEvents` test | Validate the pattern matches |
| Target type and ARN | Lambda, SFN, SQS, ECS, API destination | Determines target config |
| Existing rules on the bus | `aws events list-rules --event-bus-name <bus>` | Don't collide names; detect circular deps |
| Existing targets per rule | `aws events list-targets-by-rule` | Identify gaps and duplicates |
| Region(s) | Multi-region vs single-region | Drives global-endpoint decision |

**If the input is malformed** (no event source, ambiguous target),
emit:

```text
ARCHITECTURE: <reference>
BUS: <bus-name or "unknown">
VERDICT: ERROR
REASON: Cannot design workflow — event source and target are required inputs.
GAP: Re-supply the source service (e.g., aws.guardduty), detail-type, and the desired target.
```

## Process — Architecture design (apply in order)

### Step 0: Expert knowledge — non-obvious EventBridge behaviors

Step 0 expert-knowledge bullets (PutEvents semantics, pattern vs transformer, per-target retry, quotas, API-destination limits, cross-region, schema discovery, archive replay) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand a design decision depends on a non-obvious EventBridge behaviour.

### Step 1: Choose the event bus

| Bus type | Use when | Example events |
|---|---|---|
| **default** | AWS service events from EC2, GuardDuty, Security Hub, CloudWatch, CodeBuild, Auto Scaling, S3 | `aws.ec2`, `aws.guardduty`, `aws.securityhub` |
| **custom** | Application events from your services | `my.app.order`, `my.app.user` |
| **partner** | SaaS partner events (Datadog, Auth0, Stripe, Zendesk) | `aws.partner/datadog.com/*`, `aws.partner/stripe.com/*` |

Decision rule: default bus for AWS service events; custom bus for
application events; partner bus only when integrating with a SaaS
partner that has an EventBridge integration.

Cross-bus routing is not supported — a rule on the default bus cannot
match events on a custom bus. Use a Lambda on the default bus that
re-publishes to the custom bus if cross-bus routing is required.

### Step 2: Write the event pattern

Common pattern elements:

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

Filter operators:

| Operator | Use |
|---|---|
| `["value1", "value2"]` | OR exact match |
| `{"prefix": "ord-"}` | String prefix |
| `{"suffix": "-prod"}` | String suffix |
| `{"contains": ["error"]}` | Substring (case-sensitive) |
| `{"equals-ignore-case": "true"}` | Case-insensitive exact |
| `{"numeric": [">=", 7]}` | Numeric comparison (also `>`, `<`, `<=`, `=`, ranges) |
| `{"cidr": "10.0.0.0/8"}` | IP CIDR match |
| `{"exists": true}` | Field presence (or `false` for absence) |
| `{"anything-but": ["dev"]}` | Negation |

Validate before deploying:

```bash
aws events test-event-pattern \
  --event-pattern file://pattern.json \
  --event file://sample-event.json
```

A pattern that returns no matches on a real event sample will never
fire in production. Always test.

### Step 3: Choose target type

| Target | Use | Pros | Cons |
|---|---|---|---|
| **Lambda** | Custom logic, lightweight transformations | Fast invocation, simple | 15-min timeout; not for heavy processing |
| **Step Functions** | Multi-step orchestration, error handling, long-running | State, retries, branching | Higher per-invocation cost |
| **SQS** | Decouple producer from consumer; buffering | Backpressure handling | Requires separate consumer |
| **SNS** | Fan-out to multiple subscribers | Many subscribers | No filtering (use SQS subs with filters) |
| **API destination** | External HTTP/S endpoint | Webhook delivery | Rate-limit, credential management |
| **ECS task** | Run a containerized job | Full runtime flexibility | Slower startup; cost |
| **Systems Manager** | Run an Automation runbook | Native AWS ops integration | Async execution |
| **Batch** | Submitted job queue | Job scheduling, retries | Overkill for simple tasks |
| **Redshift Data API** | Run SQL on Redshift | Direct data warehouse access | Cluster availability dependency |
| **API Gateway** | Trigger a REST endpoint | Existing API reuse | Auth surface |
| **Pipe (separate service)** | Stream/queue source with enrichment | Decoupled, at-scale | Separate API |

Target wiring pattern:

Step 3 target wiring CLI (put-targets with DeadLetterConfig + RetryPolicy, lambda add-permission for events.amazonaws.com) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand emitting the exact wiring commands for a rule target.

A missing invocation permission produces silent non-delivery (events
match the rule but the Lambda is never invoked). This is the most
common EventBridge production failure.

### Step 4: Configure retry policy and DLQ

Every target MUST have BOTH a retry policy and a DLQ. Defaults
(185 retries, 24h max age) are usually too aggressive — tune to your
consumer's behavior.

| Workload | RetryAttempts | EventAge | DLQ |
|---|---|---|---|
| Fast, transient failures (Lambda throttled) | 3 | 900s (15 min) | Yes |
| User-facing API destination | 5 | 3600s (1h) | Yes |
| Long-running Step Functions workflow | 2 | 86400s (24h) | Yes |
| Compliance audit (must not lose) | 185 (default) | 86400s | Yes |

Create the DLQ first, then attach:

Step 4 DLQ create-and-attach CLI moved verbatim to [references/eventbridge-targets-and-retries.md](references/eventbridge-targets-and-retries.md).
Load on demand attaching the mandatory DLQ to a target.

Wire a CloudWatch alarm on DLQ depth — non-negotiable:

Step 4 DLQ-depth CloudWatch alarm CLI moved verbatim to [references/eventbridge-targets-and-retries.md](references/eventbridge-targets-and-retries.md).
Load on demand wiring the non-negotiable DLQ-depth alarm.

### Step 5: Add idempotency to the consumer

EventBridge is at-least-once. The consumer MUST be idempotent.
Reference Lambda pattern:

Step 5 reference idempotent-consumer Lambda pattern (DynamoDB conditional-write dedup) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand writing the consumer's deduplication logic.

Key idempotency rules:
- Hash fields that uniquely identify the semantic event (not just the
  delivery — `event['id']` is per-delivery, so it does NOT dedupe
  replayed events).
- Use a conditional write (DynamoDB `attribute_not_exists`) so
  concurrent deliveries are atomically deduplicated.
- Set a TTL on the dedup table (24-72 hours) to bound storage.
- For S3-triggered workflows: dedupe on the bucket + key + etag.
- For GuardDuty: dedupe on the finding ID (not the event ID).

A consumer without idempotency is a production incident waiting to
happen — duplicate notifications, duplicate billing entries,
duplicate resource creations.

### Step 6: Detect and break circular dependencies

A circular dependency: rule A matches event X, triggers Lambda B,
Lambda B calls `PutEvents` with event Y, rule C matches event Y,
triggers Lambda D, Lambda D calls `PutEvents` with event X. The loop
runs until a quota or budget is exhausted.

Detection checklist before wiring:
1. Map every rule's pattern AND every target that calls `PutEvents`.
2. For each target that publishes events, list the event source and
   detail-type.
3. Build a graph: rule → target → published events → matching rules.
4. Any cycle is a circular dependency.

Breaking cycles:
- **Add a poison pill:** the publishing target sets a field (e.g.,
  `detail.autoGenerated: true`) that the originating rule's pattern
  excludes (`{"anything-but": [true]}`).
- **Use different buses:** rule A on bus X, Lambda B publishes to
  bus Y, rule C on bus Y. Cross-bus routing is opt-in.
- **Add a sentinel header:** EventBridge input transformer injects
  a field the originating rule won't match.

A workflow with a detected cycle MUST be classified
MANUAL_STEP_REQUIRED until the cycle is broken.

### Step 7: EventBridge Pipes

Step 7 EventBridge Pipes (create-pipe CLI, rules-vs-Pipes comparison table, start-pipe) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand the source is a stream or queue, or comparing Pipes with rules.

### Step 8: EventBridge Scheduler

Step 8 EventBridge Scheduler (create-schedule CLI, rules-vs-Scheduler trade-off table) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand configuring time-based triggers.

### Step 9: Global endpoints (multi-region failover)

Step 9 global endpoints (create-endpoint CLI, replication requirements) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand multi-region failover is required.

### Step 10: Audit and verify

Step 10 audit commands (describe-rule, list-targets-by-rule, Lambda policy, DLQ depth, CloudTrail, test-event-pattern, archive, schema registry) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand verifying a deployed workflow end to end.

## Output format

```text
ARCHITECTURE: <reference>
BUS: <bus-name>
PATTERN: <event pattern summary>
TARGETS:
  - <target-1> with <retry/DLQ config>
  - <target-2> ...
RETRY: <policy summary>
SAFETY: <DLQ, idempotency, circular-dep check>
AUDIT: <CloudTrail + CloudWatch + TestEventPattern>
VERDICT: AUTOMATED | MANUAL_STEP_REQUIRED
GAP: <if MANUAL_STEP_REQUIRED, the specific missing piece>
TEMPLATE: <CLI snippet for rule + targets>
```

### Worked example — AUTOMATED, GuardDuty finding to Lambda

```text
ARCHITECTURE: guardduty-remediation
BUS: default
PATTERN: source=aws.guardduty, detail-type=GuardDuty Finding, detail.severity>=7
TARGETS:
  - Lambda isolate-instance (arn:aws:lambda:us-east-1:111111111111:function:isolate-instance)
    RetryPolicy: 3 attempts, 900s max age
    DeadLetterConfig: arn:aws:sqs:us-east-1:111111111111:eventbridge-guardduty-dlq
RETRY: 3 attempts / 15 min (fail-fast for security)
SAFETY: DLQ attached, idempotency via finding-id in DynamoDB, circular-dep check PASS (Lambda publishes no events)
AUDIT: CloudTrail on lambda:InvokeFunction; CloudWatch alarm on DLQ depth; TestEventPattern validated.
VERDICT: AUTOMATED
GAP: None
TEMPLATE:
  aws events put-rule --name guardduty-high-severity --event-bus-name default --event-pattern '{"source":["aws.guardduty"],"detail-type":["GuardDuty Finding"],"detail":{"severity":[{"numeric":[">=",7]}]}}'
  aws events put-targets --rule guardduty-high-severity --event-bus-name default --targets '[{"Id":"isolate-instance","Arn":"arn:aws:lambda:us-east-1:111111111111:function:isolate-instance","DeadLetterConfig":{"Arn":"arn:aws:sqs:us-east-1:111111111111:eventbridge-guardduty-dlq"},"RetryPolicy":{"MaximumRetryAttempts":3,"MaximumEventAgeInSeconds":900}}]'
```

### Worked example — MANUAL_STEP_REQUIRED, missing idempotency

The MANUAL_STEP_REQUIRED worked example (CodeBuild failure notification without idempotency or DLQ) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand citing the negative-path verdict format.

## Anti-Patterns — NEVER do these things

- NEVER ship a target without a DLQ. EventBridge drops events
  silently after the retry window. A target without
  `DeadLetterConfig` is silent data loss.

- NEVER assume single-delivery. EventBridge is at-least-once. A
  consumer without idempotency will process duplicate events —
  duplicate notifications, duplicate charges, duplicate resource
  creation. Always dedupe via a deterministic key in DynamoDB.

- NEVER use the default bus for application events. The default
  bus receives AWS service events (EC2, GuardDuty, Security Hub,
  CodeBuild). Mixing application events with service events
  complicates routing, access control, and schema discovery. Use a
  custom bus for application events.

- NEVER confuse `EventPattern` with `InputTransformer`.
  `EventPattern` filters which events match. `InputTransformer`
  reshapes the matched event for the target. Trying to filter in
  the transformer (or transform in the pattern) is a silent
  no-op.

- NEVER use `aws:SourceIp` as the sole condition for restricting
  `PutEvents` on a bus. IP-based restrictions are bypassable. Use
  `aws:SourceAccount` or `aws:PrincipalOrgID`. See the
  `eventbridge-bus-policy-auditor` skill.

- NEVER assume rule ENABLED means targets receive events. A rule
  can be ENABLED with zero targets, or targets without invocation
  permissions. Always verify with `list-targets-by-rule` and a
  sample `TestEventPattern`.

- NEVER assume event ordering across rules. EventBridge does not
  guarantee delivery order across rules on the same bus. If your
  workflow depends on order (e.g., create-then-update), serialize
  via a single-target Step Functions workflow that reads from SQS
  in FIFO mode.

- NEVER skip the circular-dependency check. A loop in the rule
  graph runs until a quota is hit or a target fails — at which
  point you've spammed downstream systems. Always build a
  topology map before wiring the second rule.

- NEVER set `MaximumEventAgeInSeconds` to 86400 (24h) for
  user-facing notifications. A 24-hour-old notification is worse
  than no notification. Use 900-3600s for time-sensitive
  workflows.

- NEVER use EventBridge rules for cron-style schedules when
  EventBridge Scheduler is available. Scheduler gives per-schedule
  management, timezone support, and start/end windows. Rules are
  the legacy path for time-based triggers.

- NEVER forget the Lambda invocation permission. A target without
  `lambda:AddPermission` for `events.amazonaws.com` produces
  silent non-delivery. The rule matches; the Lambda never runs.

- NEVER assume `PutEvents` from a Lambda fan-out is idempotent.
  If your Lambda publishes events to EventBridge, retried Lambda
  invocations produce duplicate published events. Apply
  idempotency at the publishing Lambda too.

- NEVER archive events on a high-volume bus without a retention
  cap. Archives bill per-event-month. A 1M events/day bus with
  90-day retention is 90M event-months — a significant line
  item. Default to 7-30 days for operational replay.

- NEVER enable schema discovery on a bus that receives
  untrusted publisher events. Schema discovery captures event
  shapes; attacker-crafted events pollute the registry.

- NEVER use `PutEvents` to deliver payloads over 256 KB. The API
  rejects them. Park large payloads in S3 and reference by URI in
  the event detail. Same for batched `PutEvents` calls exceeding
  2 MB total.

- NEVER assume a global endpoint replicates rules. Global endpoints
  replicate EVENTS between regional buses. Rules are regional —
  both regions must have equivalent rule configurations. A global
  endpoint without matching rules on the secondary bus fails
  silently during failover.

- NEVER deliver to an API destination without monitoring
  `InvocationHttpStatusCode`. A revoked OAuth credential or a
  rotated API key produces silent delivery failure until the DLQ
  fills. Monitor HTTP 4xx separately from 5xx.

## Pre-flight safety checks (run before applying any architecture CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing
  operation (`put-rule`, `put-targets`, `create-pipe`,
  `create-schedule`, `create-endpoint`), emit:
  `CONFIRM: About to <action> on bus <bus> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`

- **Test the pattern first.** Before `put-rule`, run
  `test-event-pattern` against a known-good sample event. A pattern
  that returns no matches in test will never fire in production.

- **Verify the DLQ exists** before `put-targets`. A target reference
  to a non-existent DLQ ARN produces silent non-delivery on the
  first failure.

- **Verify the Lambda invocation permission** after `put-targets`:
  `aws lambda get-policy --function-name <fn> --query 'Policy'`.
  A missing `events.amazonaws.com` principal is the most common
  silent failure.

- **Map the rule graph** before adding a new rule that triggers a
  publishing Lambda. Detect cycles. A circular dependency cascades
  silently.

- **For global endpoints**, verify both regional buses have
  equivalent rules and targets. A failover to a bus without
  matching rules is silent event loss.

## Appendix A — Event pattern operators

Appendix A operator reference table moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand authoring an event pattern filter.

## Appendix B — Common AWS event patterns

Appendix B common AWS event-pattern catalog (EC2, GuardDuty, Security Hub, CodeBuild, Auto Scaling, S3, CloudWatch, Sign-In, IAM) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand matching a common AWS service event.

## Appendix C — Decision tree (which architecture)

```
Is the source an AWS service event?
├─ Yes → Use the default bus.
│        └─ Is it a stream/queue source (DynamoDB Streams, Kinesis, SQS, MQ)?
│           ├─ Yes → Use EventBridge Pipes (Step 7).
│           └─ No  → Rule + target on default bus.
└─ No  → Is it time-based (cron/rate)?
        ├─ Yes → Use EventBridge Scheduler (Step 8).
        └─ No  → Custom bus + rule + target.

For rule + target workflows:
- Always attach DLQ (Step 4).
- Always add idempotency to the consumer (Step 5).
- Always run the circular-dependency check (Step 6).
- For multi-region resilience, use global endpoints (Step 9).
```

## Recent AWS features (2024-2026)

Recent AWS features (global endpoints GA, Scheduler, Pipes enhancements, Schema Registry, API destinations, PutEvents limits) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand checking whether a newer AWS feature changes the design.

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — the MANUAL_STEP_REQUIRED worked example (CodeBuild) and the reference idempotent-consumer Lambda pattern, moved from SKILL.md.
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — Step 3 target wiring CLI and Step 10 audit/verify commands, moved from SKILL.md.
- [references/advanced-patterns.md](references/advanced-patterns.md) — mindset, Step 0 expert knowledge, Steps 7-9 (Pipes, Scheduler, global endpoints), Appendix A operators, Appendix B event-pattern catalog, and recent AWS features, moved from SKILL.md.
- [references/eventbridge-targets-and-retries.md](references/eventbridge-targets-and-retries.md) — target/retry/DLQ reference, plus the Step 4 DLQ attach and DLQ-alarm CLI moved from SKILL.md.

## Domain

AWS CloudOps / App Integration — Event-Driven Architecture.

## AWS documentation

- **Amazon EventBridge User Guide** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-what-is.html
- **EventBridge Pipes** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-pipes.html
- **EventBridge Scheduler** — https://docs.aws.amazon.com/scheduler/latest/UserGuide/what-is-scheduler.html
- **EventBridge Global Endpoints** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-global-endpoints.html
- **EventBridge Schema Registry** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html
- **EventBridge Events from AWS Services** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-service-event.html
