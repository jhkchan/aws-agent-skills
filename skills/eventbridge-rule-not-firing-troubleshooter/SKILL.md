---
name: eventbridge-rule-not-firing-troubleshooter
description: 'Diagnoses Amazon EventBridge rules that fail to fire through a ten-category diagnostic tree: event pattern mismatch (source, detail-type, detail JSON path), content-based filtering errors (prefix, numeric, exists, anything-but, nested path depth limits), input transformer malformed templates, dead-letter queue configuration gaps, custom bus vs default bus mismatch, schedule expression syntax errors (cron vs rate vs fixed-rate), IAM role for target invocation (cross-account events.amazonaws.com principal), EventBus resource-based policy blocking PutEvents, target Lambda resource-based policy missing EventBridge principal, and event source mapping for Kinesis/Stream targets. Walks symptoms to a verified root cause with evidence-backed probes; emits ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline pattern classification works from pasted rule definitions and event samples. Live-account diagnosis uses aws events describe-rule, describe-event-bus, list-targets-by-rule, test-event-pattern, put-events (dry validate), aws lambda get-policy, aws cloudtrail lookup-events, aws iam simulate-principal-policy, aws logs filter-log-events, and aws events list-archives / replay (AWS CLI v2, SSO or key-based...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AppIntegration
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing an EventBridge rule that is not triggering its targets (event pattern mismatch, schedule expression syntax error, DLQ filling, bus mismatch, cross-account target invocation failure, input transformer error, content-based filter too strict, EventBus policy blocking PutEvents, target Lambda missing EventBridge principal), walking a symptom to the failed layer with verify and fix commands, or validating why a known event does not match a rule.
  when_not_to_use: 'EventBridge Pipe configuration debugging (use the Pipe source/target/filter JSON separately), SaaS partner integration onboarding (use the partner provider setup docs), CloudWatch Events legacy API migration (use the events: prefix migration guide), IAM policy authoring for the target invocation role (use iam-least-privilege-advisor), or Step Functions orchestration debugging (use the Step Functions execution history). This skill diagnoses rule-firing failures; it does not author event patterns from scratch or tune Pipe configurations.'
  activation_triggers: ''
  invocation_schema: '''Input: either (a) a symptom description ("rule not firing", "DLQ filling", "target Lambda never invoked"), optionally paired with the rule definition (describe-rule output), the event bus name, and a sample event payload, OR (b) a RuleName plus EventBusName for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {PATTERN_SOURCE_MISMATCH, PATTERN_DETAIL_TYPE_MISMATCH, PATTERN_DETAIL_PATH_MISMATCH, CONTENT_FILTER_TOO_STRICT, CONTENT_FILTER_NESTED_DEPTH, INPUT_TRANSFORMER_ERROR, DLQ_MISCONFIGURED, BUS_MISMATCH, SCHEDULE_SYNTAX, TARGET_IAM_ROLE, TARGET_LAMBDA_PERMISSION, EVENTBUS_POLICY, EVENT_SOURCE_MAPPING, UNKNOWN}.'''
  invocation_example: '"# Minimal valid input (offline pattern classification):\nSymptom: \"EventBridge rule ev-orders-prod-rule\nis not firing. Events are being put on the bus successfully (200\nOK from PutEvents) but the target Lambda is never invoked.\"\nEventBusName: custom.orders-bus\nRuleName: ev-orders-prod-rule\nEventPattern:\n  source: [\"myapp.orders\"]\n  detail-type: [\"Order Created\"]\n  detail:\n    status: [\"confirmed\"]\nSampleEvent:\n  source: \"myapp.orders\"\n  detail-type: \"Order Created\"\n  detail: { \"status\": \"pending\", \"orderId\": \"12345\" }"'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: EventBridge, event pattern, rule not firing, content-based filtering, input transformer, dead-letter queue, DLQ, custom bus, default bus, schedule expression, cron, rate, PutEvents, events.amazonaws.com, target Lambda permissions, cross-account, EventBus policy, event source mapping, Kinesis, troubleshooting
---

# EventBridge Rule Not Firing Troubleshooter

## Quick start

Quick-start insights and gotchas moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

## Mindset

Mindset reasoning moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

## Philosophy

Philosophy behaviours moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

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

Account-wide pre-flight command block moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

### Rule-state short-circuit

Rule-state short-circuit table moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

### Bus existence check

Bus existence check command moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

If the bus does not exist, the rule was created on a non-existent bus.
Events put on a different (or default) bus will never match. This is
BUS_MISMATCH.

### Input validation gate

INSUFFICIENT_DATA re-prompt template moved to
[references/worked-examples.md](references/worked-examples.md).

## Process — Diagnostic decision tree (apply in symptom order)

The diagnostic tree is symptom-driven. Pick the entry point based on the
observed symptom, then walk the layer-specific probes in order. Each
layer ends with either a positive root-cause confirmation (failing probe
that matches the symptom) or a pass that moves to the next layer.
**Never emit ROOT_CAUSE_IDENTIFIED without a failing probe that matches
the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

Step 0 non-obvious behaviours moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

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

test-event-pattern probe commands moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

Result interpretation and routing moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

#### 2b: Identify the mismatched field

Compare each pattern field against the event field:

Pattern-field match table moved to
[references/event-pattern-reference.md](references/event-pattern-reference.md).

Common mismatch patterns table moved to
[references/event-pattern-reference.md](references/event-pattern-reference.md).

**Verdicts:**
- `source` mismatch: ROOT_CAUSE_IDENTIFIED,
  `LAYER: PATTERN_SOURCE_MISMATCH`.
- `detail-type` mismatch: ROOT_CAUSE_IDENTIFIED,
  `LAYER: PATTERN_DETAIL_TYPE_MISMATCH`.
- `detail` path mismatch (wrong key, wrong value, type mismatch):
  ROOT_CAUSE_IDENTIFIED, `LAYER: PATTERN_DETAIL_PATH_MISMATCH`.

### Step 3: Schedule expression — cron and rate syntax

Schedule expression probe and gate moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

#### 3a: Validate the schedule expression syntax

Cron/rate syntax validation tables moved to
[references/schedule-and-permissions-reference.md](references/schedule-and-permissions-reference.md).

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

DLQ inspection commands moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

DLQ errorMessage mapping table moved to
[references/error-handling.md](references/error-handling.md).

#### 4b: Validate input transformer templates

Input transformer inspection command moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

Input transformer rules and error table moved to
[references/error-handling.md](references/error-handling.md).

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

Rule IAM role check commands moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

Step 5a verdict and same-account note moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

#### 5b: Check the target Lambda resource-based policy

Lambda get-policy probe moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

The policy MUST include a statement allowing `lambda:InvokeFunction`
for principal `events.amazonaws.com` with a `SourceArn` condition
matching the rule ARN:

Required policy statement and add-permission fix moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

Common target permission failure patterns moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

### Step 6: EventBus policy — PutEvents AccessDenied

Symptom: `PutEvents` returns `AccessDenied` or
`NotAuthorizedForSourceException`.

EventBus policy probe and cross-account policy example moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

If the policy is missing or does not list the source account,
**ROOT_CAUSE_IDENTIFIED**, `LAYER: EVENTBUS_POLICY`.

put-event-bus-policy fix command moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

For same-account PutEvents with a custom bus, the account automatically
has `events:PutEvents` — no policy needed. An AccessDenied here
indicates an SCP or permissions boundary issue.

### Step 7: Input transformer — target receives wrong data

Symptom: the rule fires and the target is invoked, but the target
receives unexpected or malformed data.

Input transformer inspection command moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

Input transformer data-shape validation moved to
[references/schedule-and-permissions-reference.md](references/schedule-and-permissions-reference.md).

### Step 8: Bus mismatch — custom bus vs default bus

Symptom: events are successfully put on one bus, but the rule is on
another bus.

Bus mismatch probes (rule bus vs PutEvents bus) moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

If the rule's `EventBusName` differs from the PutEvents entry's
`eventBusName`, the events are on a different bus. **ROOT_CAUSE_IDENTIFIED**,
`LAYER: BUS_MISMATCH`.

Bus mismatch patterns table moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

Fix: align the PutEvents `EventBusName` parameter with the rule's
`EventBusName`, OR recreate the rule on the correct bus.

### Step 9: Event source mapping — Kinesis/DynamoDB Streams

Symptom: an EventBridge rule triggers a Lambda that is supposed to
process Kinesis or DynamoDB Stream records, but no records are
received.

The Lambda event source mapping is a separate delivery path from
EventBridge. If the Lambda's trigger is the Kinesis stream (not the
EventBridge rule), diagnose the event source mapping:

Event source mapping probe moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

Event source mapping checklist moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

### Step 10: Content-based filtering — operators and depth limits

Symptom: `test-event-pattern` returns false for an event that should
match. The pattern uses content-based filtering operators.

#### 10a: Validate content filter operators

Content filter operator and failure tables moved to
[references/event-pattern-reference.md](references/event-pattern-reference.md).

#### 10b: Check nested path depth

Count the depth of the JSON path in the pattern. EventBridge caps at
10 levels of nesting for content-based filtering.

Nested depth limit illustration moved to
[references/event-pattern-reference.md](references/event-pattern-reference.md).

If the pattern references a path at depth > 10, **ROOT_CAUSE_IDENTIFIED**,
`LAYER: CONTENT_FILTER_NESTED_DEPTH`. Fix: flatten the event structure
before putting it on the bus, or restructure the pattern to reference a
shallower path.

If the content filter operator is misapplied (type mismatch, wrong
operator for the value type), **ROOT_CAUSE_IDENTIFIED**,
`LAYER: CONTENT_FILTER_TOO_STRICT`.

### Step 11: Verify with TestEventPattern (final confirmation)

Verification command and guidance moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

### Step 12: INSUFFICIENT_DATA

If none of the above produced a positive root-cause match, emit:

INSUFFICIENT_DATA output template moved to
[references/worked-examples.md](references/worked-examples.md).

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

Worked example (schedule expression syntax) moved to
[references/worked-examples.md](references/worked-examples.md).

### Worked example — Target Lambda missing EventBridge principal

Worked example (target Lambda missing principal) moved to
[references/worked-examples.md](references/worked-examples.md).

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

Pre-flight safety checks moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

## Remediation guidance

Per-verdict fix commands moved to
[references/error-handling.md](references/error-handling.md).

## Deep reference: EventBridge rule-firing layer model

Layer model deep reference tables moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

## Recent AWS features (2024-2026)

Recent AWS features moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — quick-start insights, mindset, philosophy, Step 0 non-obvious behaviours, failure-pattern tables, layer-model deep reference, recent AWS features (moved from this file)
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight commands, safety checks, and every step's probe/fix command listings (moved from this file)
- [references/error-handling.md](references/error-handling.md) — DLQ errorMessage mapping, input-transformer error table, per-verdict remediation fixes (moved from this file)
- [references/worked-examples.md](references/worked-examples.md) — INSUFFICIENT_DATA re-prompt templates and secondary worked examples (moved from this file)
- [references/event-pattern-reference.md](references/event-pattern-reference.md) — pattern matching model, content-filter operators, nested depth limits (moved-from tables appended)
- [references/schedule-and-permissions-reference.md](references/schedule-and-permissions-reference.md) — schedule expressions, target/bus permissions, input transformer reference (moved-from tables appended)

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
