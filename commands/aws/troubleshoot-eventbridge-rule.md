---
description: Diagnose Amazon EventBridge rules that fail to fire through a ten-category diagnostic tree (event pattern mismatch, content-based filtering, input transformer errors, DLQ configuration, bus mismatch, schedule syntax, target IAM role, target Lambda permissions, EventBus policy, event source mapping) — emits ROOT_CAUSE_IDENTIFIED with the specific failure layer or INSUFFICIENT_DATA.
nl_triggers:
  - "EventBridge rule not firing"
  - "EventBridge rule not triggering"
  - "event pattern does not match"
  - "EventBridge DLQ filling"
  - "EventBridge dead-letter queue"
  - "EventBridge schedule expression error"
  - "EventBridge cron syntax"
  - "EventBridge rate expression"
  - "PutEvents AccessDenied"
  - "events.amazonaws.com principal"
  - "EventBridge target Lambda not invoked"
  - "EventBridge cross-account target"
  - "EventBus policy"
  - "input transformer error EventBridge"
  - "content-based filtering EventBridge"
  - "custom event bus mismatch"
  - "troubleshoot EventBridge rule"
  - "diagnose EventBridge rule failure"
routes_to: eventbridge-rule-not-firing-troubleshooter
---

# /aws:troubleshoot-eventbridge-rule

Activate the `eventbridge-rule-not-firing-troubleshooter` skill and
diagnose an Amazon EventBridge rule that is not triggering its targets
through the ten-category diagnostic tree.

## What it does

Reads a symptom description (PutEvents returns 200 but target never
fires, DLQ filling, schedule rule never fires, cross-account target
denied) plus the rule configuration, then walks the symptom-driven
diagnostic tree to a root cause with positive evidence:

1. **Pre-flight** — rule state and EventBusName
   (`describe-rule`), target list (`list-targets-by-rule`), bus
   configuration (`describe-event-bus`), and the decisive
   `test-event-pattern` probe.
   Short-circuits on `State: DISABLED` (auto-disabled for schedule
   syntax errors) or missing bus.
2. **Symptom entry** — map the symptom to one of: event pattern
   mismatch (source, detail-type, detail path), content-based
   filtering error, input transformer error, DLQ misconfiguration,
   bus mismatch, schedule expression syntax, target IAM role,
   target Lambda permission, EventBus policy, event source mapping.
3. **Layer-specific probes** —
   - Pattern: `test-event-pattern` (THE decisive probe), field-by-field
     comparison, content filter operator validation, nested depth count.
   - Schedule: field count validation (6 required), wildcard rules,
     `?` mutual exclusion, UTC timezone verification.
   - DLQ: inspect DLQ messages for `errorMessage`, validate input
     transformer template and path mappings.
   - Permissions: `lambda get-policy` for `events.amazonaws.com`
     principal, `iam simulate-principal-policy` for cross-account role,
     `describe-event-bus` for bus policy.
   - Bus: compare PutEvents `eventBusName` against rule `EventBusName`.
4. **Verdict** — ROOT_CAUSE_IDENTIFIED (with failing probe that matches
   the symptom) or INSUFFICIENT_DATA (a probe requires operator input).

Emits a deterministic diagnostic block per target:

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
```

## When to invoke

Paste a symptom description and ask any of:

- "EventBridge rule not firing"
- "PutEvents returns 200 but target Lambda never invoked"
- "EventBridge DLQ filling with events"
- "schedule-based rule never fires at expected time"
- "EventBridge cron expression error"
- "EventBridge cross-account target denied"
- "content-based filtering not matching"
- "input transformer error EventBridge"

A bare rule name + any symptom ("rule broken", "events not delivered",
"target not triggering") also routes here via the orchestrator.

## Inputs

- Symptom description: error string, observed behaviour, whether the
  rule is event-based or schedule-based, whether the target is same-
  account or cross-account.
- Rule configuration: RuleName, EventBusName, EventPattern or
  ScheduleExpression, State, Targets (Arn, InputTransformer,
  DeadLetterConfig, RoleArn).
- For live-account diagnosis: a sample event payload that SHOULD have
  triggered the rule. The skill uses `describe-rule`,
  `test-event-pattern`, `describe-event-bus`, `list-targets-by-rule`,
  `lambda get-policy`, `cloudtrail lookup-events`,
  `iam simulate-principal-policy`, `logs filter-log-events`.

## Outputs

- One diagnostic block per target rule.
- Layer-specific LAYER value from the enumerated set.
- Evidence section with the failing probe AND passing probes (layers
  ruled out) — never a verdict without positive evidence.
- Specific remediation: pattern fix, schedule expression correction,
  permission grant, bus alignment, input transformer repair, or
  EventBus policy update.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for EventBridge rule failures).
- `/aws:troubleshoot-lambda-invocation` for deeper diagnosis when the
  EventBridge target Lambda fails to process the event (timeout, OOM,
  AccessDenied from the handler).
- `/aws:troubleshoot-iam-permission` for deeper diagnosis when the
  target invocation role or EventBus policy is denied by an SCP or
  permissions boundary.
