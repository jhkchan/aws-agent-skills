---
name: eventbridge-rule-not-firing-troubleshooter
description: >-
  Diagnoses Amazon EventBridge rules that fail to fire through a ten-category
  diagnostic tree: event pattern mismatch (source, detail-type, detail JSON
  path), content-based filtering errors (prefix, numeric, exists,
  anything-but, nested path depth limits), input transformer malformed
  templates, dead-letter queue configuration gaps, custom bus vs default
  bus mismatch, schedule expression syntax errors (cron vs rate vs
  fixed-rate), IAM role for target invocation (cross-account
  events.amazonaws.com principal), EventBus resource-based policy
  blocking PutEvents, target Lambda resource-based policy missing
  EventBridge principal, and event source mapping for Kinesis/Stream
  targets. Walks symptoms to a verified root cause with evidence-backed
  probes; emits ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline pattern classification works from pasted rule definitions and event samples. Live-account diagnosis uses aws events describe-rule, describe-event-bus, list-targets-by-rule, test-event-pattern, put-events (dry validate), aws lambda get-policy, aws cloudtrail lookup-events, aws iam simulate-principal-policy, aws logs filter-log-events, and aws events list-archives / replay (AWS CLI v2, SSO or key-based credentials).
keywords:
- EventBridge
- event pattern
- rule not firing
- content-based filtering
- input transformer
- dead-letter queue
- DLQ
- custom bus
- default bus
- schedule expression
- cron
- rate
- PutEvents
- events.amazonaws.com
- target Lambda permissions
- cross-account
- EventBus policy
- event source mapping
- Kinesis
- troubleshooting
tags:
- eventbridge
- appintegration
- troubleshooting
- event-pattern
- content-based-filtering
- schedule
- iam-role
- cross-account
- dlq
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: AppIntegration
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing an EventBridge rule that is not triggering its targets (event pattern mismatch, schedule expression syntax error, DLQ filling, bus mismatch, cross-account target invocation failure, input transformer error, content-based filter too strict, EventBus policy blocking PutEvents, target Lambda missing EventBridge principal), walking a symptom to the failed layer with verify and fix commands, or validating why a known event does not match a rule.
  when_not_to_use: EventBridge Pipe configuration debugging (use the Pipe source/target/filter JSON separately), SaaS partner integration onboarding (use the partner provider setup docs), CloudWatch Events legacy API migration (use the events: prefix migration guide), IAM policy authoring for the target invocation role (use iam-least-privilege-advisor), or Step Functions orchestration debugging (use the Step Functions execution history). This skill diagnoses rule-firing failures; it does not author event patterns from scratch or tune Pipe configurations.
  activation_triggers:
  - EventBridge rule not firing
  - EventBridge rule not triggering
  - event pattern does not match
  - EventBridge DLQ filling
  - EventBridge dead-letter queue
  - EventBridge schedule expression error
  - EventBridge cron syntax
  - EventBridge rate expression
  - PutEvents AccessDenied
  - events.amazonaws.com principal
  - EventBridge target Lambda not invoked
  - EventBridge cross-account target
  - EventBus policy
  - input transformer error EventBridge
  - content-based filtering EventBridge
  - custom event bus mismatch
  - troubleshoot EventBridge rule
  invocation_schema: 'Input: either (a) a symptom description ("rule not firing", "DLQ filling", "target Lambda never invoked"), optionally paired with the rule definition (describe-rule output), the event bus name, and a sample event payload, OR (b) a RuleName plus EventBusName for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {PATTERN_SOURCE_MISMATCH, PATTERN_DETAIL_TYPE_MISMATCH, PATTERN_DETAIL_PATH_MISMATCH, CONTENT_FILTER_TOO_STRICT, CONTENT_FILTER_NESTED_DEPTH, INPUT_TRANSFORMER_ERROR, DLQ_MISCONFIGURED, BUS_MISMATCH, SCHEDULE_SYNTAX, TARGET_IAM_ROLE, TARGET_LAMBDA_PERMISSION, EVENTBUS_POLICY, EVENT_SOURCE_MAPPING, UNKNOWN}.'
  invocation_example: "# Minimal valid input (offline pattern classification):\nSymptom: \"EventBridge rule ev-orders-prod-rule\nis not firing. Events are being put on the bus successfully (200\nOK from PutEvents) but the target Lambda is never invoked.\"\nEventBusName: custom.orders-bus\nRuleName: ev-orders-prod-rule\nEventPattern:\n  source: [\"myapp.orders\"]\n  detail-type: [\"Order Created\"]\n  detail:\n    status: [\"confirmed\"]\nSampleEvent:\n  source: \"myapp.orders\"\n  detail-type: \"Order Created\"\n  detail: { \"status\": \"pending\", \"orderId\": \"12345\" }"
---

# EventBridge Rule Not Firing Troubleshooter

## Quick start

- **Symptom → layer map (first plausible match drives the first probe):**
  PutEvents returns 200 but target never fires → PATTERN mismatch or
  BUS_MISMATCH or TARGET permission; DLQ filling → DLQ_MISCONFIGURED or
  INPUT_TRANSFORMER_ERROR or PATTERN mismatch (rejected events);
  schedule-based rule never fires → SCHEDULE_SYNTAX; cross-account
  target Lambda never invoked → TARGET_IAM_ROLE or
  TARGET_LAMBDA_PERMISSION; PutEvents returns AccessDenied →
  EVENTBUS_POLICY; content-based filter seems correct but event does
  not match → CONTENT_FILTER_TOO_STRICT or
  CONTENT_FILTER_NESTED_DEPTH.
- **An event pattern is a FILTER, not a transformation.** The pattern
  declares what the event MUST contain to trigger the rule; it does not
  modify the event. Operators who write patterns expecting the event to
  be reshaped are confused when events do not match. Every field in the
  pattern is an AND condition — all must match for the rule to fire.
- **Content-based filtering JSON path has a maximum depth of 10 levels.**
  A pattern referencing `$.detail.a.b.c.d.e.f.g.h.i.j` (11 levels) will
  silently fail to match because EventBridge caps nested JSON path
  resolution at 10 levels. No error is emitted — the rule simply never
  fires for events whose matching value lives at depth 11+.
- **The target Lambda resource-based policy must allow
  `lambda:InvokeFunction` for the `events.amazonaws.com` principal.**
  EventBridge assumes a service-linked role to invoke targets, but the
  target Lambda itself must grant the EventBridge service principal via
  its resource-based policy. Without this, the rule fires (visible in
  CloudTrail) but the invocation is silently denied.
- **Always verify with `test-event-pattern`, never guess.** The single
  most decisive probe is `aws events test-event-pattern` — it returns a
  boolean match/no-match and eliminates all ambiguity about whether the
  pattern matches the event.

## Mindset

An EventBridge rule that "does not fire" is almost always a pattern
matching problem, not a routing problem. The EventBridge service is
extremely reliable at delivering matched events; the failure is in the
match logic (pattern does not correspond to the event shape), the bus
routing (event put on bus A, rule on bus B), the schedule expression
(syntax error silently disables the rule), or the target permissions
(the rule fires but the target invocation is denied). Senior
integration engineers start with `test-event-pattern` and the rule's
`State` field, not by re-creating the rule.

## Philosophy

Four behaviours separate a senior EventBridge engineer from a generalist:

- **The event pattern is a declarative filter, not an imperative
  transformation.** Every key in the pattern is a condition that the
  event MUST satisfy. `source: ["myapp"]` means the event's `source`
  field must exactly equal `"myapp"`. `detail-type: ["Order Created"]`
  means the event's `detail-type` must exactly equal `"Order Created"`.
  There is no fuzzy matching, no regex, no partial match. Operators who
  expect `"myapp.orders"` to match a pattern of `["myapp"]` are
  confused — the comparison is exact-string, not prefix, unless the
  `prefix` content filter operator is explicitly used.

- **Content-based filtering operators are powerful but have silent
  failure modes.** The `prefix`, `numeric`, `exists`, `anything-but`,
  `wildcard`, and `cidr` operators extend matching beyond exact string
  equality, but each has quirks: `prefix` matches on string values only
  (not numbers), `numeric` requires the value to be a JSON number (not
  a string containing digits), `exists` true/false inverts the check,
  and nested JSON paths beyond 10 levels silently fail to resolve. An
  operator that looks syntactically correct can fail to match because
  the value type does not match the operator's expectation.

- **The EventBus is a routing boundary, not just a namespace.** An
  event put on the default bus (`aws.events`) will never match a rule
  on a custom bus (`custom.my-bus`), and vice versa. The `EventBusName`
  parameter in `PutEvents` and `put-rule` must be the same.
  Operators who put events on the default bus and create rules on a
  custom bus see zero matches and assume the pattern is wrong — the
  pattern is fine, the buses are different.

- **Cross-account and cross-service target invocation requires BOTH
  the EventBridge rule's IAM role AND the target's resource-based
  policy.** EventBridge assumes a service-linked role to invoke
  targets, but for cross-account Lambda targets, the target Lambda's
  resource-based policy must explicitly allow
  `lambda:InvokeFunction` from `events.amazonaws.com` with a
  `SourceArn` condition matching the rule ARN. Missing either side
  silently drops the invocation.

## Quick reference — symptom triage table

| Symptom phrase / error | Most likely layer | First probe |
|---|---|---|
| PutEvents returns 200 but target never fires | PATTERN mismatch / BUS_MISMATCH / TARGET permission | `test-event-pattern` with the rule pattern and a sample event |
| DLQ filling with events | PATTERN mismatch / INPUT_TRANSFORMER_ERROR / DLQ_MISCONFIGURED | Inspect DLQ messages for `errorMessage` field |
| Schedule-based rule never fires at expected time | SCHEDULE_SYNTAX | `describe-rule` (ScheduleExpression), validate cron/rate syntax |
| Cross-account target Lambda never invoked | TARGET_IAM_ROLE / TARGET_LAMBDA_PERMISSION | `lambda get-policy` on target; `iam simulate-principal-policy` on rule role |
| PutEvents returns AccessDenied | EVENTBUS_POLICY | `events describe-event-bus` (policy), cross-account PutEvents permissions |
| `test-event-pattern` returns false for a known-good event | PATTERN_DETAIL_PATH_MISMATCH / CONTENT_FILTER_TOO_STRICT | Compare event JSON against pattern field by field |
| Rule `State: DISABLED` | SCHEDULE_SYNTAX (auto-disabled) or manual disable | `describe-rule` State field |
| EventBridge input transformer: "InputTemplate is invalid" | INPUT_TRANSFORMER_ERROR | `describe-rule` InputTransformers, validate template syntax |
| Nested detail path > 10 levels never matches | CONTENT_FILTER_NESTED_DEPTH | Count JSON path depth in pattern vs EventBridge 10-level cap |

## Pre-flight: rule state and gather-info gate

Before running symptom-specific probes, gather the canonical rule
configuration and short-circuit on rule states that mimic firing
failures. Misclassifying these produces hours of pattern debugging for
a problem that is not a pattern problem.

### Account-wide pre-flight commands

```bash
# 1. Rule configuration (EventPattern, ScheduleExpression, State,
#    EventBusName, Targets, RoleArn)
aws events describe-rule \
  --name <rule-name> --event-bus-name <bus-name> --output json

# 2. List targets for the rule (Target Id, Arn, InputTransformers,
#    DeadLetterConfig, RetryPolicy)
aws events list-targets-by-rule \
  --rule <rule-name> --event-bus-name <bus-name> --output json

# 3. Event bus configuration (Name, Policy, source-type)
aws events describe-event-bus \
  --name <bus-name> --output json

# 4. Test the event pattern against a sample event (THE decisive probe)
aws events test-event-pattern \
  --event-pattern '<json-pattern-from-rule>' \
  --event '<sample-event-json>' --output json

# 5. Recent EventBridge API calls (CloudTrail)
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=PutEvents \
  --start-time $(date -d '-1 hour' +%s) --end-time $(date +%s) \
  --output json
```

### Rule-state short-circuit

| `State` | Effect on diagnosis |
|---|---|
| `ENABLED` | Proceed with pattern/bus/target diagnosis. |
| `DISABLED` | The rule was manually disabled OR EventBridge auto-disabled it after a schedule expression syntax error. Check `ScheduleExpression` for syntax errors; re-enable with `enable-rule`. |
| `ENABLED` with `ManagedBy: [SVC]` | AWS service-managed rule (e.g., CloudWatch Alarm → SNS). Do not modify directly; the owning service controls state. |

### Bus existence check

```bash
aws events list-event-buses --name-prefix <bus-name> --output json
```

If the bus does not exist, the rule was created on a non-existent bus.
Events put on a different (or default) bus will never match. This is
BUS_MISMATCH.

### Input validation gate

If the input is malformed (missing RuleName, absent EventBusName, no
sample event for pattern diagnosis), emit:

```text
TARGET: <rule-name or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context — at minimum the RuleName,
  the EventBusName, and a sample event payload to test against the
  pattern.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the RuleName and
  EventBusName, (2) a sample event that SHOULD have triggered the
  rule, and (3) for schedule-based rules, the ScheduleExpression
  string.
```

## Process — Diagnostic decision tree (apply in symptom order)

The diagnostic tree is symptom-driven. Pick the entry point based on the
observed symptom, then walk the layer-specific probes in order. Each
layer ends with either a positive root-cause confirmation (failing probe
that matches the symptom) or a pass that moves to the next layer.
**Never emit ROOT_CAUSE_IDENTIFIED without a failing probe that matches
the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

These are the operational gotchas a senior EventBridge engineer knows
from incident experience. Each one routes a diagnosis away from the
obvious layer to a less obvious one:

- **EventBridge silently auto-disables rules with invalid schedule
  expressions.** If a cron or rate expression has a syntax error (wrong
  number of fields, invalid wildcard position, unsupported day-of-week
  value), EventBridge sets the rule State to DISABLED without emitting
  an error event. The operator sees "rule not firing" and assumes a
  pattern issue. Always check `State: DISABLED` as a first signal for
  schedule-based rules.

- **The `test-event-pattern` API is the single most decisive probe.**
  It takes the exact pattern from the rule and a sample event and
  returns `{"Result": true}` or `{"Result": false}`. This eliminates
  ALL ambiguity about whether the pattern matches. Operators who eyeball
  the pattern against the event are wrong ~30% of the time because of
  case sensitivity, array vs scalar wrapping, and content filter
  operator quirks.

- **Content-based filtering supports a maximum nesting depth of 10
  levels in the JSON path.** A pattern referencing
  `detail.level1.level2.level3.level4.level5.level6.level7.level8.
  level9.level10` works; adding `level11` silently fails. EventBridge
  does not emit an error — the path is simply unresolvable, and the
  rule never fires for events whose value lives at depth 11+. Flatten
  deeply nested structures before putting them on the bus, or restructure
  the pattern to reference a shallower path.

- **The `source` and `detail-type` fields are case-sensitive exact
  string matches.** `"Order Created"` does not match `"order created"`
  or `"OrderCreated"`. AWS service-emitted events use specific casing
  (e.g., `"aws.ec2"` for source, `"EC2 Instance State-change
  Notification"` for detail-type). Always copy the exact strings from
  the event, not from memory.

- **The `detail` field in the pattern is matched against the `detail`
  field in the event — not against the top-level event.** A pattern
  with `detail: { status: ["confirmed"] }` matches an event with
  `"detail": { "status": "confirmed" }`, NOT an event with
  `"status": "confirmed"` at the top level. Operators who put their
  payload fields at the top level of the PutEvents entry (instead of
  inside `detail`) never match detail-based patterns.

- **PutEvents returns 200 even if no rule matches.** The PutEvents API
  response indicates successful ingestion onto the bus, not successful
  rule matching. A 200 with `FailedEntryCount: 0` means the event was
  accepted; whether any rule fires depends on pattern matching. Operators
  who see 200 and conclude "the rule should have fired" are conflating
  ingestion with matching.

- **Input transformer errors send the original event to the DLQ, not
  the transformed event.** If the input transformer template references
  a JSON path that does not exist in the event, the transformation fails
  silently and the event is routed to the DLQ (if configured) or dropped
  (if not). The DLQ message contains an `errorMessage` field explaining
  the transformation failure.

- **Cross-account PutEvents requires the bus policy to explicitly grant
  `events:PutEvents` to the source account.** The default bus and
  custom buses do not allow cross-account PutEvents by default. The
  bus policy must include a statement allowing
  `events:PutEvents` from the source account ARN.

- **The target Lambda resource-based policy must allow
  `events.amazonaws.com` as principal, not the rule's IAM role ARN.**
  EventBridge invokes Lambda via its service principal, not via
  `sts:AssumeRole` on the rule's role. The `SourceArn` condition in the
  Lambda policy should match the rule ARN for least privilege.

- **EventBridge cron expressions have 6 fields (not 5 like standard
  cron), do NOT support the `?` wildcard in the year field, and use
  `L` (last day of month) and `W` (nearest weekday) modifiers.** A
  standard 5-field cron expression pasted into EventBridge silently
  fails. Rate expressions use `rate(value unit)` where unit is
  `minutes`/`hours`/`days` (not `m`/`h`/`d`).

- **Event source mapping for Kinesis/Stream targets is configured on
  the target side (Lambda event source mapping), not on the
  EventBridge rule.** An EventBridge rule that triggers a Lambda which
  reads from Kinesis has two independent trigger paths. If the Kinesis
  stream is the actual event source, the EventBridge rule is not the
  delivery mechanism — check the Lambda event source mapping
  (`get-event-source-mapping`) for Kinesis-specific issues (shard
  iterator, batch size, starting position).

### Step 1: Symptom entry — pick the diagnostic branch

Map the symptom to a branch and jump to that branch's section. If the
symptom matches none of the categories, route to Step 12
(INSUFFICIENT_DATA).

| Symptom | Branch |
|---|---|
| PutEvents 200, target never fires, rule has EventPattern | Step 2 — Pattern diagnosis |
| Rule has ScheduleExpression, never fires at expected time | Step 3 — Schedule expression |
| DLQ filling with events | Step 4 — DLQ and input transformer |
| Cross-account target Lambda never invoked | Step 5 — Target permissions |
| PutEvents returns AccessDenied | Step 6 — EventBus policy |
| Rule fires but target receives wrong/unexpected data | Step 7 — Input transformer |
| Custom bus in play, events not matching | Step 8 — Bus mismatch |
| Kinesis/DynamoDB Stream target not receiving | Step 9 — Event source mapping |
| `test-event-pattern` returns false for known-good event | Step 10 — Content-based filtering |
| None of the above | Step 12 — INSUFFICIENT_DATA |

### Step 2: Event pattern mismatch — source, detail-type, detail path

Symptom: PutEvents returns 200, the rule is ENABLED, but the target
never fires. The most common cause is a pattern that does not match
the event.

#### 2a: Run test-event-pattern (THE decisive probe)

```bash
# Extract the pattern from the rule
PATTERN=$(aws events describe-rule \
  --name <rule-name> --event-bus-name <bus-name> \
  --output json | jq '.EventPattern')

# Test against a sample event
aws events test-event-pattern \
  --event-pattern "$PATTERN" \
  --event '<sample-event-json>' --output json
```

If `Result: false`, the pattern does not match. Proceed to 2b to
identify which field mismatches.

If `Result: true`, the pattern matches — the issue is downstream (bus
mismatch, target permissions, DLQ). Proceed to Steps 5-8.

#### 2b: Identify the mismatched field

Compare each pattern field against the event field:

| Pattern field | Event field | Match rule |
|---|---|---|
| `source` | `source` | Exact string match (case-sensitive). Array = OR. |
| `detail-type` | `detail-type` | Exact string match (case-sensitive). Array = OR. |
| `detail.{path}` | `detail.{path}` | Exact value match. Content filter operators apply. |
| `account` | `account` | Exact string match. Array = OR. |
| `region` | `region` | Exact string match. Array = OR. |
| `time` | `time` | Not matched as a pattern field (timestamp). Use content filters on `detail.time` if needed. |
| `resources` | `resources` | Exact ARN match. Array = OR. |

Common mismatch patterns:

| Pattern | Event | Result | Fix |
|---|---|---|---|
| `source: ["myapp"]` | `source: "myapp.orders"` | No match | Use `source: ["myapp.orders"]` or `source: [{prefix: "myapp"}]` |
| `detail-type: ["Order Created"]` | `detail-type: "order created"` | No match | Case-sensitive — use exact casing |
| `detail: {status: ["confirmed"]}` | `detail: {status: "pending"}` | No match | Add "pending" to the array or change the condition |
| `detail: {amount: [100]}` | `detail: {amount: "100"}` | No match | Type mismatch — number vs string |
| `detail: {order: {id: ["123"]}}` | event has `detail.order.id = "123"` at depth 3 | Match (depth is within limit) | Verify depth ≤ 10 |

**Verdicts:**
- `source` mismatch: ROOT_CAUSE_IDENTIFIED,
  `LAYER: PATTERN_SOURCE_MISMATCH`.
- `detail-type` mismatch: ROOT_CAUSE_IDENTIFIED,
  `LAYER: PATTERN_DETAIL_TYPE_MISMATCH`.
- `detail` path mismatch (wrong key, wrong value, type mismatch):
  ROOT_CAUSE_IDENTIFIED, `LAYER: PATTERN_DETAIL_PATH_MISMATCH`.

### Step 3: Schedule expression — cron and rate syntax

Symptom: a schedule-based rule (no EventPattern, has
ScheduleExpression) never fires at the expected time, or the rule's
State is DISABLED.

```bash
aws events describe-rule \
  --name <rule-name> --event-bus-name <bus-name> \
  --output json | jq '{ScheduleExpression, State}'
```

#### 3a: Validate the schedule expression syntax

**Cron expressions** have 6 required fields:
`Minutes Hours Day-of-month Month Day-of-week Year`

| Field | Values | Wildcards |
|---|---|---|
| Minutes | 0-59 | `,` `-` `*` `/` |
| Hours | 0-23 | `,` `-` `*` `/` |
| Day-of-month | 1-31 | `,` `-` `*` `/` `?` `L` `W` |
| Month | 1-12 or JAN-DEC | `,` `-` `*` `/` |
| Day-of-week | 1-7 or SUN-SAT | `,` `-` `*` `/` `?` `L` `#` |
| Year | 1970-2199 | `,` `-` `*` `/` |

Common cron syntax errors:

| Expression | Error | Fix |
|---|---|---|
| `cron(0 12 * * ? *)` | Correct — runs at 12:00 UTC daily | — |
| `cron(0 12 * * * *)` | Missing `?` for day-of-week/day-of-month mutual exclusion | Use `?` in one of the two fields: `cron(0 12 * * ? *)` |
| `cron(0 12 * * ?)` | Missing year field (5-field cron) | Add year: `cron(0 12 * * ? *)` |
| `cron(* 0 1 * * *)` | Both day-of-month and day-of-week are `*` (ambiguous) | Use `?` in one: `cron(* 0 1 * ? *)` |
| `cron(0 12 31 2 * *)` | February 31 does not exist | Use valid date |
| `rate(5 m)` | Wrong unit format | Use `rate(5 minutes)` |
| `rate(1 hour)` | Correct | — |

**Rate expressions** use `rate(value unit)`:
- value: positive integer
- unit: `minute(s)`, `hour(s)`, `day(s)` (singular if value=1, plural if >1)
- minimum: `rate(1 minute)`
- cannot be `rate(0 ...)` — minimum is 1

**Important:** EventBridge cron uses UTC. A rule set to
`cron(0 9 * * ? *)` fires at 09:00 UTC, not local time. Operators in
UTC+8 see the rule fire at 17:00 local and assume it is broken.

#### 3b: Check for auto-disable

If `State: DISABLED` on a schedule rule, EventBridge auto-disabled it
after detecting a syntax error in the ScheduleExpression. Fix the
expression syntax and re-enable:

```bash
aws events enable-rule --name <rule-name> --event-bus-name <bus-name>
```

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: SCHEDULE_SYNTAX`. Fix:
correct the expression syntax, re-enable the rule.

### Step 4: Dead-letter queue and input transformer errors

Symptom: the DLQ configured on the target is filling with messages.
Each DLQ message contains the original event plus metadata about why
delivery failed.

#### 4a: Inspect DLQ messages

```bash
# For SQS DLQ:
aws sqs receive-message --queue-url <dlq-url> \
  --max-number-of-messages 5 --output json

# Extract the errorMessage field from each message body
aws sqs receive-message --queue-url <dlq-url> \
  --max-number-of-messages 5 --output json | \
  jq '.Messages[].Body | fromjson | .errorMessage // .'
```

The `errorMessage` field in the DLQ message body identifies the failure
reason:

| errorMessage pattern | Cause | Layer |
|---|---|---|
| `"InputTemplate is invalid"` or `"Invalid template"` | Input transformer template has a syntax error | INPUT_TRANSFORMER_ERROR |
| `"Path ... is not present"` | Input transformer references a JSON path absent from the event | INPUT_TRANSFORMER_ERROR |
| `"ResourceArn"` or `"AccessDenied"` | Target invocation denied (permissions) | TARGET_IAM_ROLE / TARGET_LAMBDA_PERMISSION |
| No errorMessage, event body present | Rule matched, target invocation failed at the target side | Depends on target-side probe |

#### 4b: Validate input transformer templates

```bash
aws events describe-rule \
  --name <rule-name> --event-bus-name <bus-name> \
  --output json | jq '.Targets[0].InputTransformer'
```

Input transformer rules:
- `InputPathsMap`: maps template variables to JSON paths from the event
  (e.g., `"order_id": "$.detail.orderId"`).
- `InputTemplate`: a string template referencing the variables (e.g.,
  `"{\"orderId\": \"<order_id>\"}"`).
- Every variable in the template MUST have a corresponding path in
  `InputPathsMap`.
- If the JSON path in `InputPathsMap` does not exist in the event, the
  transformation fails.
- The template MUST produce valid JSON if the target expects JSON
  (Lambda, Step Functions).

Common input transformer errors:

| Error | Cause | Fix |
|---|---|---|
| Template references `<var>` but `InputPathsMap` has no `var` | Missing path mapping | Add the path to `InputPathsMap` |
| Path `$.detail.nested.field` does not exist in event | Event shape changed | Update the path or ensure the event contains the field |
| Template produces invalid JSON | Missing quote, extra comma | Validate the template output with `jq` |

**Verdicts:**
- Input transformer error: ROOT_CAUSE_IDENTIFIED,
  `LAYER: INPUT_TRANSFORMER_ERROR`.
- DLQ misconfigured (wrong ARN, DLQ deleted, DLQ in different region):
  ROOT_CAUSE_IDENTIFIED, `LAYER: DLQ_MISCONFIGURED`.

### Step 5: Target permissions — IAM role and Lambda resource policy

Symptom: the rule fires (visible in CloudTrail as `PutRule` /
successful invocation attempt), but the target Lambda is never invoked
or receives AccessDenied.

#### 5a: Check the rule's IAM role (for cross-account targets)

```bash
aws events describe-rule \
  --name <rule-name> --event-bus-name <bus-name> \
  --output json | jq '.RoleArn'
```

If `RoleArn` is present, the rule uses an IAM role to invoke targets.
For cross-account Lambda targets:

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <role-arn> \
  --action-names lambda:InvokeFunction \
  --resource-arns <target-lambda-arn> \
  --output json
```

If `implicitDeny`, the role lacks `lambda:InvokeFunction` on the target.
**ROOT_CAUSE_IDENTIFIED**, `LAYER: TARGET_IAM_ROLE`.

For same-account targets, EventBridge uses a service-linked role and
does NOT require a RoleArn on the rule. The target's resource-based
policy is the gate.

#### 5b: Check the target Lambda resource-based policy

```bash
aws lambda get-policy --function-name <target-lambda> --output json 2>/dev/null
```

The policy MUST include a statement allowing `lambda:InvokeFunction`
for principal `events.amazonaws.com` with a `SourceArn` condition
matching the rule ARN:

```json
{
  "Effect": "Allow",
  "Principal": {"Service": "events.amazonaws.com"},
  "Action": "lambda:InvokeFunction",
  "Condition": {"ArnLike": {"AWS:SourceArn": "arn:aws:events:<region>:<account>:rule/<bus>/<rule-name>"}},
  "Resource": "<lambda-arn>"
}
```

If the statement is missing, the EventBridge service principal cannot
invoke the Lambda. **ROOT_CAUSE_IDENTIFIED**,
`LAYER: TARGET_LAMBDA_PERMISSION`.

Fix:

```bash
aws lambda add-permission \
  --function-name <target-lambda> \
  --statement-id EventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:<region>:<account>:rule/<bus>/<rule-name> \
  --output json
```

#### 5c: Common target permission failure patterns

| Pattern | Cause |
|---|---|
| Same-account Lambda, no resource-based policy for events.amazonaws.com | Missing EventBridge principal grant. Add via `lambda add-permission`. |
| Cross-account Lambda, rule has no RoleArn | EventBridge cannot assume a role to invoke cross-account. Add a RoleArn with `lambda:InvokeFunction` on the target. |
| Cross-account Lambda, RoleArn present but role lacks `lambda:InvokeFunction` | Role identity-based policy missing the permission. |
| Cross-account Lambda, role has permission but target lacks resource-based policy | Both sides must allow for cross-account. Add the resource-based policy statement. |
| SourceArn condition mismatch | The condition's ArnLike pattern does not match the actual rule ARN (e.g., wrong bus name in the ARN). |
| Multiple rules targeting same Lambda | Each rule needs its own `add-permission` statement (or a wildcard SourceArn, which is less secure). |

### Step 6: EventBus policy — PutEvents AccessDenied

Symptom: `PutEvents` returns `AccessDenied` or
`NotAuthorizedForSourceException`.

```bash
aws events describe-event-bus --name <bus-name> --output json | jq '.Policy'
```

For cross-account PutEvents (account B putting events on a bus in
account A):

The bus policy in account A MUST grant `events:PutEvents` to account B:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::<account-b-id>:root"},
    "Action": "events:PutEvents",
    "Resource": "arn:aws:events:<region>:<account-a-id>:event-bus/<bus-name>"
  }]
}
```

If the policy is missing or does not list the source account,
**ROOT_CAUSE_IDENTIFIED**, `LAYER: EVENTBUS_POLICY`.

Fix:

```bash
aws events put-event-bus-policy \
  --event-bus-name <bus-name> \
  --policy '<json-policy>' --output json
```

For same-account PutEvents with a custom bus, the account automatically
has `events:PutEvents` — no policy needed. An AccessDenied here
indicates an SCP or permissions boundary issue.

### Step 7: Input transformer — target receives wrong data

Symptom: the rule fires and the target is invoked, but the target
receives unexpected or malformed data.

```bash
aws events describe-rule \
  --name <rule-name> --event-bus-name <bus-name> \
  --output json | jq '.Targets[0].InputTransformer, .Targets[0].InputPath'
```

If `InputTransformer` is absent and `InputPath` is absent, the target
receives the full event envelope (including `version`, `id`, `source`,
`detail-type`, etc.). If the target expects only the `detail` field,
configure `InputPath: "$.detail"`.

If `InputTransformer` is present, validate:
1. Every variable in `InputTemplate` has a mapping in `InputPathsMap`.
2. Every JSON path in `InputPathsMap` exists in the actual event.
3. The template produces valid JSON for JSON-expecting targets.

See Step 4b for detailed transformer validation.

### Step 8: Bus mismatch — custom bus vs default bus

Symptom: events are successfully put on one bus, but the rule is on
another bus.

```bash
# What bus does the rule live on?
aws events describe-rule --name <rule-name> --output json | jq '.EventBusName'

# What bus was the event put on?
# Check CloudTrail for the PutEvents call:
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=PutEvents \
  --start-time $(date -d '-1 hour' +%s) --end-time $(date +%s) \
  --output json | jq '.Events[0].CloudTrailEvent | fromjson |
    .requestParameters.entries[0].eventBusName'
```

If the rule's `EventBusName` differs from the PutEvents entry's
`eventBusName`, the events are on a different bus. **ROOT_CAUSE_IDENTIFIED**,
`LAYER: BUS_MISMATCH`.

Common bus mismatch patterns:

| Rule EventBusName | PutEvents EventBusName | Result |
|---|---|---|
| `custom.orders` | `default` (or omitted) | No match — events on default bus, rule on custom |
| `default` | `custom.orders` | No match — events on custom bus, rule on default |
| `custom.orders` | `custom.orders` | Correct — same bus |

Fix: align the PutEvents `EventBusName` parameter with the rule's
`EventBusName`, OR recreate the rule on the correct bus.

### Step 9: Event source mapping — Kinesis/DynamoDB Streams

Symptom: an EventBridge rule triggers a Lambda that is supposed to
process Kinesis or DynamoDB Stream records, but no records are
received.

The Lambda event source mapping is a separate delivery path from
EventBridge. If the Lambda's trigger is the Kinesis stream (not the
EventBridge rule), diagnose the event source mapping:

```bash
aws lambda get-event-source-mapping \
  --function-name <lambda-name> --output json 2>/dev/null
```

Check:
- `State: Enabled` — the mapping is active.
- `BatchSize` — reasonable for the throughput.
- `StartingPosition: LATEST` vs `TRIM_HORIZON` — LATEST skips old
  records; TRIM_HORIZON reads from the earliest available.
- `FunctionResponseTypes: [ReportBatchItemFailures]` — enables
  partial batch failure reporting.

If the mapping is disabled or misconfigured, the Lambda never receives
records regardless of the EventBridge rule configuration.

### Step 10: Content-based filtering — operators and depth limits

Symptom: `test-event-pattern` returns false for an event that should
match. The pattern uses content-based filtering operators.

#### 10a: Validate content filter operators

| Operator | Syntax | Matches | Common error |
|---|---|---|---|
| `prefix` | `{"prefix": "ord"}` | Strings starting with "ord" | Applied to non-string value (number, boolean) |
| `numeric` | `{"numeric": [">=", 100]}` | Numbers ≥ 100 | Applied to string value `"100"` |
| `equals-ignore-case` | `{"equals-ignore-case": "abc"}` | String "abc" case-insensitive | Only works on strings, not numbers |
| `any-but` | `{"anything-but": ["cancelled"]}` | Any value except "cancelled" | Does not match null/undefined |
| `wildcard` | `{"wildcard": "ord-*"}` | Strings matching glob "ord-*" | Only `*` is supported (no `?`) |
| `cidr` | `{"cidr": "10.0.0.0/8"}` | IP addresses in CIDR range | Only IPv4 |
| `exists` | `{"exists": true}` | Field is present | `{"exists": false}` = field is absent |

Common content filter failure patterns:

| Pattern | Event | Result | Why |
|---|---|---|---|
| `{"prefix": "ord"}` on `detail.type` | `detail.type: 123` | No match | `prefix` works on strings only |
| `{"numeric": [">=", 100]}` on `detail.amount` | `detail.amount: "150"` | No match | Value is string, not number |
| `{"exists": true}` on `detail.optional` | Event has no `detail.optional` | No match | Field genuinely absent |
| `{"anything-but": ["x"]}` on `detail.tag` | Event has no `detail.tag` | No match | Missing field does not match anything-but |

#### 10b: Check nested path depth

Count the depth of the JSON path in the pattern. EventBridge caps at
10 levels of nesting for content-based filtering.

```text
detail                          → depth 1
detail.level1                   → depth 2
detail.level1.level2            → depth 3
...
detail.l1.l2.l3.l4.l5.l6.l7.l8.l9 → depth 10 (maximum)
detail.l1.l2.l3.l4.l5.l6.l7.l8.l9.l10 → depth 11 (FAILS SILENTLY)
```

If the pattern references a path at depth > 10, **ROOT_CAUSE_IDENTIFIED**,
`LAYER: CONTENT_FILTER_NESTED_DEPTH`. Fix: flatten the event structure
before putting it on the bus, or restructure the pattern to reference a
shallower path.

If the content filter operator is misapplied (type mismatch, wrong
operator for the value type), **ROOT_CAUSE_IDENTIFIED**,
`LAYER: CONTENT_FILTER_TOO_STRICT`.

### Step 11: Verify with TestEventPattern (final confirmation)

After identifying the likely root cause and proposing a fix, always
verify the corrected pattern:

```bash
aws events test-event-pattern \
  --event-pattern '<corrected-pattern-json>' \
  --event '<sample-event-json>' --output json
```

`Result: true` confirms the corrected pattern matches. Only then
update the rule.

### Step 12: INSUFFICIENT_DATA

If none of the above produced a positive root-cause match, emit:

```text
TARGET: <rule-name>
VERDICT: INSUFFICIENT_DATA
REASON: The available evidence does not conclusively identify a root
  cause. One or more probes returned ambiguous results or required
  operator input that was not provided.
LAYER: UNKNOWN
EVIDENCE:
  - <list what was probed and what was inconclusive>
REMEDIATION: Provide: (1) a sample event payload that should have
  triggered the rule, (2) the output of `describe-rule` including
  EventBusName and Targets, (3) for schedule-based rules, the exact
  ScheduleExpression string, and (4) for cross-account targets, the
  target Lambda's resource-based policy.
```

## Output format

```text
TARGET: <rule-name on bus-name>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <PATTERN_SOURCE_MISMATCH | PATTERN_DETAIL_TYPE_MISMATCH |
        PATTERN_DETAIL_PATH_MISMATCH | CONTENT_FILTER_TOO_STRICT |
        CONTENT_FILTER_NESTED_DEPTH | INPUT_TRANSFORMER_ERROR |
        DLQ_MISCONFIGURED | BUS_MISMATCH | SCHEDULE_SYNTAX |
        TARGET_IAM_ROLE | TARGET_LAMBDA_PERMISSION |
        EVENTBUS_POLICY | EVENT_SOURCE_MAPPING | UNKNOWN>
EVIDENCE:
  - <observed symptom — error string or behaviour>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <rule-name> in <region>.
  Proceed? (yes/no)"
```

### Worked example — Pattern detail-type mismatch

```text
TARGET: ev-orders-prod-rule on custom.orders-bus
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The rule's EventPattern filters on detail-type "Order Created"
  but the sample event has detail-type "OrderCreated" (no space). The
  test-event-pattern API returns Result: false. The source and detail
  fields match; only the detail-type value differs by casing and
  spacing (Step 2b).
LAYER: PATTERN_DETAIL_TYPE_MISMATCH
EVIDENCE:
  - Symptom: PutEvents returns 200 with FailedEntryCount: 0 for events
    on custom.orders-bus, but the target Lambda is never invoked. The
    rule State is ENABLED.
  - Probe: aws events test-event-pattern with the rule's pattern and
    the sample event returns {"Result": false}.
  - Probe: Field-by-field comparison shows source matches ("myapp.orders"
    = "myapp.orders"), detail.status matches ("confirmed" in both), but
    detail-type does NOT match: pattern has "Order Created", event has
    "OrderCreated".
  - Passing: EventBusName matches (custom.orders-bus in both PutEvents
    and rule); rule State is ENABLED; target Lambda has
    events.amazonaws.com principal in its resource-based policy.
REMEDIATION:
  1. Update the rule's EventPattern to match the actual detail-type:
     aws events put-rule --name ev-orders-prod-rule \
       --event-bus-name custom.orders-bus \
       --event-pattern '{"source":["myapp.orders"],"detail-type":["OrderCreated"],"detail":{"status":["confirmed"]}}'
  2. Verify the fix:
     aws events test-event-pattern \
       --event-pattern '{"source":["myapp.orders"],"detail-type":["OrderCreated"],"detail":{"status":["confirmed"]}}' \
       --event '<sample-event>' --output json
     Expected: {"Result": true}
CONFIRM: Before updating the rule, emit and await:
  "CONFIRM: About to update ev-orders-prod-rule EventPattern on
   custom.orders-bus. Proceed? (yes/no)"
```

### Worked example — Schedule expression syntax

```text
TARGET: ev-nightly-report-rule on default bus
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The rule's ScheduleExpression is "cron(0 9 * * *)" which has
  only 5 fields. EventBridge cron requires 6 fields (including Year).
  EventBridge auto-disabled the rule (State: DISABLED) due to the
  syntax error (Step 3a/3b).
LAYER: SCHEDULE_SYNTAX
EVIDENCE:
  - Symptom: schedule-based rule ev-nightly-report-rule never fires.
    describe-rule shows State: DISABLED.
  - Probe: aws events describe-rule returns ScheduleExpression:
    "cron(0 9 * * *)" and State: DISABLED.
  - Probe: The cron expression has 5 fields; EventBridge requires 6
    (Minutes Hours Day-of-month Month Day-of-week Year).
  - Passing: EventBusName is default (correct); the target Lambda has
    events.amazonaws.com principal; no EventPattern on the rule
    (schedule-based, not event-based).
REMEDIATION:
  1. Update the ScheduleExpression to use 6 fields:
     aws events put-rule --name ev-nightly-report-rule \
       --schedule-expression "cron(0 9 * * ? *)"
  2. Re-enable the rule (it was auto-disabled):
     aws events enable-rule --name ev-nightly-report-rule
  3. Verify:
     aws events describe-rule --name ev-nightly-report-rule \
       --output json | jq '{State, ScheduleExpression}'
     Expected: State: ENABLED, ScheduleExpression: "cron(0 9 * * ? *)"
CONFIRM: Before updating the rule, emit and await:
  "CONFIRM: About to update ev-nightly-report-rule schedule expression
   and re-enable. Proceed? (yes/no)"
```

### Worked example — Target Lambda missing EventBridge principal

```text
TARGET: ev-order-processor-rule on custom.orders-bus
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The rule fires (test-event-pattern returns true, CloudTrail
  shows successful PutEvents), but the target Lambda fn-order-processor
  is never invoked. The Lambda's resource-based policy has no statement
  allowing events.amazonaws.com to invoke it. EventBridge's invocation
  is silently denied (Step 5b).
LAYER: TARGET_LAMBDA_PERMISSION
EVIDENCE:
  - Symptom: PutEvents returns 200; test-event-pattern returns Result:
    true; but the Lambda's CloudWatch logs show zero invocations.
  - Probe: aws lambda get-policy on fn-order-processor returns a policy
    with statements for API Gateway and S3, but NO statement for
    events.amazonaws.com.
  - Probe: aws cloudtrail lookup-events for the Lambda ARN in the last
    hour shows EventBridge invocation attempts returning AccessDenied.
  - Passing: EventBusName matches; rule State is ENABLED; pattern
    matches the event (test-event-pattern: true); rule has no RoleArn
    (same-account, service-linked role path).
REMEDIATION:
  1. Add the EventBridge principal to the Lambda resource-based policy:
     aws lambda add-permission \
       --function-name fn-order-processor \
       --statement-id EventBridgeInvoke \
       --action lambda:InvokeFunction \
       --principal events.amazonaws.com \
       --source-arn arn:aws:events:us-east-1:111111111111:rule/custom.orders-bus/ev-order-processor-rule
  2. Verify:
     aws lambda get-policy --function-name fn-order-processor \
       --output json | jq '.Policy | fromjson | .Statement[] |
         select(.Principal.Service == "events.amazonaws.com")'
     Expected: a statement with Action lambda:InvokeFunction and
     SourceArn matching the rule ARN.
CONFIRM: Before adding the permission, emit and await:
  "CONFIRM: About to add EventBridge invoke permission to
   fn-order-processor. Proceed? (yes/no)"
```

## Anti-Patterns — NEVER

- NEVER declare ROOT_CAUSE_IDENTIFIED without a failing probe that
  matches the symptom. A "process of elimination" diagnosis erodes
  operator trust when the real cause is elsewhere.

- NEVER assume `test-event-pattern` is unnecessary because "the pattern
  looks right." Exact-string case sensitivity, type mismatches
  (number vs string), and content filter operator quirks cause ~30% of
  patterns that "look right" to fail. Always run the API.

- NEVER confuse the default bus with a custom bus. Events on the
  default bus never match rules on a custom bus, and vice versa. Always
  verify `EventBusName` in both the PutEvents call and the rule
  definition.

- NEVER use a 5-field cron expression in EventBridge. EventBridge cron
  requires exactly 6 fields including Year. A 5-field expression
  (standard Linux cron) silently fails and may auto-disable the rule.

- NEVER assume PutEvents 200 means the rule should have fired. PutEvents
  200 means the event was ingested onto the bus. Whether any rule
  fires depends entirely on pattern matching, which is a separate step.

- NEVER grant `events.amazonaws.com` permission on the target Lambda
  without a `SourceArn` condition. A bare `events.amazonaws.com`
  principal allows ANY EventBridge rule in the account to invoke the
  Lambda. Always scope with `SourceArn` matching the specific rule ARN.

- NEVER assume the `detail` field in the pattern matches top-level
  event fields. `detail: {status: ["confirmed"]}` matches
  `event.detail.status`, NOT `event.status`. The three matched
  top-level fields are `source`, `detail-type`, and `resources` (plus
  `account`, `region`, and `time` as metadata).

- NEVER nest content-based filter paths deeper than 10 levels.
  EventBridge silently fails to resolve JSON paths beyond depth 10 in
  the `detail` object. Flatten the structure or restructure the pattern.

- NEVER assume EventBridge auto-disables only for schedule syntax. While
  schedule syntax is the most common auto-disable cause, sustained
  target invocation failures (thousands of consecutive failures) can
  also trigger auto-disable for some target types.

- NEVER confuse EventBridge event source mapping with Lambda event
  source mapping. An EventBridge rule triggering a Lambda is one path;
  a Lambda reading from Kinesis/DynamoDB Streams via event source
  mapping is an entirely separate path. Diagnose the correct one.

- NEVER use `rate(0 ...)` as a schedule expression. The minimum rate is
  `rate(1 minute)`. A value of 0 is invalid and auto-disables the rule.

- NEVER assume `{"exists": false}` means "the field is falsy." It means
  "the field is ABSENT from the JSON." A field with value `null` or
  `""` is PRESENT — `exists: false` does NOT match it.

- NEVER apply `prefix` or `wildcard` operators to non-string values. A
  numeric field `{"amount": 150}` does not match
  `{"prefix": "15"}` — the operator works on strings only.

- NEVER update a rule's EventPattern or ScheduleExpression without
  re-testing with `test-event-pattern` (for event-based rules) or
  validating the cron/rate syntax (for schedule-based rules). A
  syntactically broken update can auto-disable the rule.

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`put-rule`, `enable-rule`, `disable-rule`, `put-targets`,
  `remove-targets`, `put-event-bus-policy`, `lambda add-permission`),
  emit and await operator approval. Do NOT execute the CLI until the
  operator confirms.

- **Read-only first.** Every probe in the diagnostic tree is
  read-only (`describe-rule`, `test-event-pattern`, `describe-event-bus`,
  `list-targets-by-rule`, `get-policy`, `lookup-events`,
  `simulate-principal-policy`). Do not perform state-changing
  operations as diagnostic probes.

- **`put-rule` with the same name overwrites** the existing rule's
  configuration. Always include the full EventPattern or
  ScheduleExpression; omitting a field reverts it to default.

- **`enable-rule` / `disable-rule`** toggle the rule state. Enabling a
  rule with a still-broken schedule expression re-triggers
  auto-disable. Fix the expression before re-enabling.

- **`put-targets` adds to the existing target list** unless
  `--event-bus-name` and the existing target Ids are managed carefully.
  Use `remove-targets` to clear old targets before adding new ones if
  the target configuration changes substantively.

- **`lambda add-permission`** adds a statement to the resource-based
  policy. Duplicate statement IDs overwrite. Each EventBridge rule
  targeting the same Lambda needs a unique statement ID.

- **Bulk remediation batch limit.** If the diagnosis identifies the
  same root cause across multiple rules (e.g., a missing
  `events.amazonaws.com` principal after a Lambda recreation), batch
  remediation into groups of at most 5 rules, emit a single CONFIRM
  per batch, and verify between batches.

## Remediation guidance

### For PATTERN_SOURCE_MISMATCH

```bash
aws events put-rule --name <rule-name> \
  --event-bus-name <bus-name> \
  --event-pattern '<corrected-pattern-with-matching-source>'
```

### For PATTERN_DETAIL_TYPE_MISMATCH

Update the `detail-type` array to include the exact string from the
event (case-sensitive):

```bash
aws events put-rule --name <rule-name> \
  --event-bus-name <bus-name> \
  --event-pattern '<corrected-pattern-with-matching-detail-type>'
```

### For PATTERN_DETAIL_PATH_MISMATCH

Update the `detail` path to reference the correct key and value type:

```bash
aws events put-rule --name <rule-name> \
  --event-bus-name <bus-name> \
  --event-pattern '{"source":["..."],"detail-type":["..."],"detail":{"correctKey":["correctValue"]}}'
```

### For CONTENT_FILTER_TOO_STRICT

Fix the operator type mismatch (e.g., use `numeric` for number values,
`prefix` for strings only):

```bash
aws events put-rule --name <rule-name> \
  --event-bus-name <bus-name> \
  --event-pattern '{"detail":{"amount":{"numeric":[">=",100]}}}'
```

### For CONTENT_FILTER_NESTED_DEPTH

Flatten the event structure before PutEvents, or restructure the
pattern to reference a shallower path (depth ≤ 10).

### For INPUT_TRANSFORMER_ERROR

Fix the template and path mappings:

```bash
aws events put-targets --rule <rule-name> \
  --event-bus-name <bus-name> \
  --targets '[{"Id":"1","Arn":"<target-arn>","InputTransformer":{"InputPathsMap":{"order_id":"$.detail.orderId"},"InputTemplate":"{\"orderId\": \"<order_id>\"}"}}]'
```

### For DLQ_MISCONFIGURED

Configure or correct the DLQ ARN on the target:

```bash
aws events put-targets --rule <rule-name> \
  --event-bus-name <bus-name> \
  --targets '[{"Id":"1","Arn":"<target-arn>","DeadLetterConfig":{"Arn":"arn:aws:sqs:<region>:<account>:<dlq-name>"}}]'
```

### For BUS_MISMATCH

Align the PutEvents EventBusName with the rule's EventBusName, or
recreate the rule on the correct bus.

### For SCHEDULE_SYNTAX

```bash
aws events put-rule --name <rule-name> \
  --schedule-expression "cron(0 9 * * ? *)"
aws events enable-rule --name <rule-name>
```

### For TARGET_IAM_ROLE

Add `lambda:InvokeFunction` to the rule's IAM role on the target ARN:

```bash
aws iam put-role-policy --role-name <role-name> \
  --policy-name <policy-name> \
  --policy-document '<JSON granting lambda:InvokeFunction on target ARN>'
```

### For TARGET_LAMBDA_PERMISSION

```bash
aws lambda add-permission \
  --function-name <target-lambda> \
  --statement-id EventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:<region>:<account>:rule/<bus>/<rule-name>
```

### For EVENTBUS_POLICY

```bash
aws events put-event-bus-policy \
  --event-bus-name <bus-name> \
  --policy '<json-granting-events:PutEvents-to-source-account>'
```

## Deep reference: EventBridge rule-firing layer model

### Symptom → layer decision matrix (offline classification)

```
Error string / symptom                          → Layer
test-event-pattern returns false                 → PATTERN_*_MISMATCH / CONTENT_FILTER_*
DLQ filling                                      → INPUT_TRANSFORMER_ERROR / DLQ_MISCONFIGURED
ScheduleExpression State: DISABLED               → SCHEDULE_SYNTAX
Cross-account Lambda never invoked               → TARGET_IAM_ROLE / TARGET_LAMBDA_PERMISSION
PutEvents AccessDenied                           → EVENTBUS_POLICY
Events on bus A, rule on bus B                   → BUS_MISMATCH
Nested path > 10 levels never matches            → CONTENT_FILTER_NESTED_DEPTH
```

### EventBridge event structure (canonical)

```json
{
  "version": "0",
  "id": "abc123-...",
  "detail-type": "Order Created",
  "source": "myapp.orders",
  "account": "111111111111",
  "time": "2026-08-05T12:00:00Z",
  "region": "us-east-1",
  "resources": ["arn:aws:s3:::my-bucket/order-123"],
  "detail": {
    "orderId": "12345",
    "status": "confirmed",
    "amount": 150
  }
}
```

The pattern matches against `source`, `detail-type`, `detail`,
`account`, `region`, and `resources`. The `version`, `id`, and `time`
fields are metadata and are not pattern-matched.

### Cron expression reference (6 fields)

```
Field             Values             Wildcards
─────────────────────────────────────────────────────
Minutes           0-59               , - * /
Hours             0-23               , - * /
Day-of-month      1-31               , - * / ? L W
Month             1-12 or JAN-DEC    , - * /
Day-of-week       1-7 or SUN-SAT     , - * / ? L #
Year              1970-2199          , - * /
```

Rules:
- Day-of-month and Day-of-week are mutually exclusive. Use `?` in one
  to mean "no specific value."
- `L` = last (last day of month, last specific weekday).
- `W` = nearest weekday to the given day.
- `#` = nth occurrence of a weekday in the month (e.g., `2#1` = first
  Monday).

### Rate expression reference

```
rate(value unit)
```
- value: positive integer (≥ 1)
- unit: `minute(s)`, `hour(s)`, `day(s)`
- singular if value = 1: `rate(1 minute)`
- plural if value > 1: `rate(5 minutes)`

### Content-based filtering operator reference

| Operator | Syntax | Works on | Example |
|---|---|---|---|
| `prefix` | `{"prefix": "abc"}` | String | `{"source": [{"prefix": "aws."}]}` |
| `numeric` | `{"numeric": [op, val, ...]}` | Number | `{"detail": {"amount": {"numeric": [">", 100]}}}` |
| `equals-ignore-case` | `{"equals-ignore-case": "abc"}` | String | `{"detail": {"type": {"equals-ignore-case": "ORDER"}}}` |
| `anything-but` | `{"anything-but": [vals]}` | Any | `{"detail": {"status": {"anything-but": ["cancelled"]}}}` |
| `wildcard` | `{"wildcard": "abc-*"}` | String | `{"detail": {"id": {"wildcard": "ord-*"}}}` |
| `cidr` | `{"cidr": "10.0.0.0/8"}` | String (IP) | `{"detail": {"ip": {"cidr": "10.0.0.0/8"}}}` |
| `exists` | `{"exists": bool}` | Any | `{"detail": {"optional_field": {"exists": true}}}` |

### Nested path depth limit

EventBridge resolves JSON paths in the `detail` object up to 10 levels
deep. Paths at depth 11+ silently fail to resolve — the rule never
fires for events whose value lives beyond depth 10.

```
$.detail                                    → depth 1
$.detail.a                                  → depth 2
$.detail.a.b                                → depth 3
$.detail.a.b.c                              → depth 4
$.detail.a.b.c.d                            → depth 5
$.detail.a.b.c.d.e                          → depth 6
$.detail.a.b.c.d.e.f                        → depth 7
$.detail.a.b.c.d.e.f.g                      → depth 8
$.detail.a.b.c.d.e.f.g.h                    → depth 9
$.detail.a.b.c.d.e.f.g.h.i                  → depth 10 (maximum)
$.detail.a.b.c.d.e.f.g.h.i.j                → depth 11 (FAILS)
```

## Recent AWS features (2024-2026)

- **EventBridge advanced JSON matching (2024):** Extended support for
  `$or` matching at the top level of the pattern, allowing alternative
  pattern branches. Diagnostically, `$or` patterns must have at least
  one branch that fully matches for the rule to fire.
- **EventBridge input transformer enhancements (2024-2025):** Increased
  template size limit and support for more complex JSON path
  expressions. Diagnostically, templates that previously exceeded the
  limit may now work without changes.
- **EventBridge Scheduler (2022-2024):** A separate service from
  EventBridge rules that provides one-time and recurring schedules with
  enhanced timezone support. Diagnostically, if the operator created
  the schedule in EventBridge Scheduler (not EventBridge rules), the
  `describe-rule` API will not find it — use `scheduler
  get-schedule`.
- **EventBridge global endpoints (2024):** Multi-region failover for
  event buses. Diagnostically, a global endpoint may route events to a
  secondary region during a failover, causing rules in the primary
  region to appear non-firing.
- **PutEvents maximum entry size (2024-2025):** 256 KB per event entry
  (up from an earlier limit). Events larger than 256 KB are rejected
  with a specific error in the PutEvents response.

## Domain

AWS CloudOps / EventBridge App Integration, Event Pattern Matching,
Schedule Expressions, Cross-Account Target Invocation, and Dead-Letter
Queue Diagnostics.

## AWS documentation

- **Amazon EventBridge User Guide — Event patterns** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html
- **Content-based filtering** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-create-pattern-operand-ref.html
- **Scheduled events (cron and rate)** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-scheduled-event-pattern.html
- **EventBridge input transformation** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-transform-target-input.html
- **EventBridge dead-letter queues** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rule-dlq.html
- **Cross-account event delivery** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-cross-account.html
- **EventBridge IAM roles** — https://docs.aws.amazon.com/eventbridge/latest/userguide/auth-and-access-control-iam.html
- **EventBridge Scheduler** — https://docs.aws.amazon.com/scheduler/latest/UserGuide/what-is-scheduler.html
- **Lambda resource-based policy for EventBridge** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-target-lambda.html
