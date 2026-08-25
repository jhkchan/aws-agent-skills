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

Mindset prose (stateless filter + fan-out dispatcher, pattern-vs-schedule fork, target wiring as the bug surface, at-least-once contract) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand framing a rule deployment.

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

The required-data command listing (event source, sample payload, target ARN, region, existing rules, producer accounts, existing DLQs) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand gathering the required inputs.

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

Step 0 expert-knowledge bullets (PutEvents ingestion, pattern JSONPath-like, per-target transformer, silent DLQ ARNs, schedule syntax, cross-account gates, size caps, API-destination limits, replay semantics, quotas, global endpoints, schema discovery) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand a plan depends on a non-obvious behaviour.

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

Step 1 put-rule CLI examples (pattern rule, cron schedule rule, rate rule) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand emitting the put-rule command for the chosen rule type.

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

Step 2 filter-operator table moved verbatim to [references/eventbridge-rules-and-targets.md](references/eventbridge-rules-and-targets.md).
Load on demand authoring an event pattern filter.

Step 2 test-event-pattern validation CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand validating the pattern before put-rule.

A pattern that returns no matches on a real sample will never fire in
production. Always test.

### Step 3: Pick target type

Step 3 target-type comparison table (Lambda, SFN, SQS, SNS, API destination, ECS, SSM, Batch, Redshift, SageMaker, API Gateway, Firehose, Inspector) moved verbatim to [references/eventbridge-rules-and-targets.md](references/eventbridge-rules-and-targets.md).
Load on demand choosing a target type.

Target wiring pattern:

Step 3 CLI (put-targets with DLQ + RetryPolicy, lambda add-permission, get-policy verification) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand emitting the target wiring commands.

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

Step 4 CLI (create-queue with 14-day retention, put-targets attach, CloudWatch DLQ-depth alarm) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand wiring retry policy, DLQ, and the DLQ alarm.

### Step 5: Configure input transformation

`InputTransformer` reshapes the matched event for the target. Two
parts: `InputPathsMap` (extract values from the event) and
`InputTemplate` (build the new payload).

Step 5 InputTransformer CLI (InputPathsMap + InputTemplate) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand configuring input transformation.

Key rules:
- `InputPathsMap` values are JSONPath strings starting with `$.`
- `<placeholder>` in `InputTemplate` references `InputPathsMap` keys
- For string values in JSON output, wrap placeholder in quotes: `"<user>"`
- For non-string values (numbers, objects, arrays), use bare: `<value>`
- A target without an `InputTransformer` receives the **full original
  event envelope** (including `version`, `id`, `time`, `source`,
  `detail-type`, `detail`, `account`, `region`)

Step 5 per-target-type InputTemplate patterns moved verbatim to [references/eventbridge-rules-and-targets.md](references/eventbridge-rules-and-targets.md).
Load on demand choosing an InputTemplate shape.

### Step 6: Deploy cross-account event routing

Step 6 cross-account CLI (receiving-bus put-permission with SourceAccount, producer PutEvents with bus ARN, org-wide PrincipalOrgID) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand deploying cross-account routing.

### Step 7: Use custom event bus vs default

Step 7 bus selection (bus-type table, create-event-bus CLI, naming conventions, cross-bus routing limit) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand choosing or creating the bus.

### Step 8: Configure archive and replay

Step 8 CLI (create-archive, start-replay) and the critical replay warnings moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand configuring archives or a replay.

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

Step 10 create-endpoint CLI and equivalence requirements moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand configuring multi-region failover.

### Step 11: Enable Schema Registry

Step 11 CLI (create-registry, create-discoverer) and schema-discovery notes moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand enabling schema discovery.

### Step 12: Verify the deployment

Step 12 verification CLI (describe-rule, list-targets-by-rule, Lambda policy, DLQ depth, bus policy, archive, test-event-pattern, CloudWatch Invocations/FailedInvocations) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand verifying the deployment end to end.

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

The PREREQUISITES_MISSING worked example (CodeBuild failure notification without DLQ/idempotency) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand citing the negative-path verdict format.

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

Appendix A operator reference table and combination note moved verbatim to [references/eventbridge-rules-and-targets.md](references/eventbridge-rules-and-targets.md).
Load on demand authoring an event pattern filter.

## Appendix B — Common AWS event sources

Appendix B common AWS event-source catalog (EC2, GuardDuty, Security Hub, CodeBuild, Auto Scaling, S3, CloudWatch, Sign-In, IAM, Health) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand matching a common AWS service event.

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

The 5-point deployment gate (pattern validates, target ARNs resolve, DLQ 14-day retention, invocation permissions, consumer idempotency noted) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand deciding READY_TO_DEPLOY vs PREREQUISITES_MISSING.

## Recent AWS features (2024-2026)

Recent AWS features (global endpoints GA, Scheduler, Pipes enhancements, Schema Registry, API destinations, PutEvents limits, PrincipalOrgID routing) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand checking whether a newer AWS feature changes the plan.

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — the PREREQUISITES_MISSING worked example (CodeBuild, no DLQ), moved from SKILL.md.
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight data sources, per-step deploy CLI (rule/targets/DLQ alarm/input-transformer/cross-account/bus/archive/global endpoints/Schema Registry), and Step 12 verification commands, moved from SKILL.md.
- [references/advanced-patterns.md](references/advanced-patterns.md) — mindset, Step 0 expert knowledge, Step 7 bus selection, Appendix B event-source catalog, the 5-point deployment gate heuristic, and recent AWS features, moved from SKILL.md.
- [references/eventbridge-rules-and-targets.md](references/eventbridge-rules-and-targets.md) — rules/targets reference, plus the Step 2/Appendix A operator table, Step 3 target-type table, and Step 5 input-transformer patterns moved from SKILL.md.

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
