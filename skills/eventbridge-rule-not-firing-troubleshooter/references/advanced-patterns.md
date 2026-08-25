# EventBridge Rule Not Firing Troubleshooter — advanced patterns (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## Quick start insights (moved from SKILL.md)

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

## Mindset (moved from SKILL.md)

An EventBridge rule that "does not fire" is almost always a pattern
matching problem, not a routing problem. The EventBridge service is
extremely reliable at delivering matched events; the failure is in the
match logic (pattern does not correspond to the event shape), the bus
routing (event put on bus A, rule on bus B), the schedule expression
(syntax error silently disables the rule), or the target permissions
(the rule fires but the target invocation is denied). Senior
integration engineers start with `test-event-pattern` and the rule's
`State` field, not by re-creating the rule.

## Philosophy (moved from SKILL.md)

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

## Step 0: Non-obvious behaviours that change diagnosis (moved from SKILL.md)

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

## Common target permission failure patterns (moved from SKILL.md)

#### 5c: Common target permission failure patterns

| Pattern | Cause |
|---|---|
| Same-account Lambda, no resource-based policy for events.amazonaws.com | Missing EventBridge principal grant. Add via `lambda add-permission`. |
| Cross-account Lambda, rule has no RoleArn | EventBridge cannot assume a role to invoke cross-account. Add a RoleArn with `lambda:InvokeFunction` on the target. |
| Cross-account Lambda, RoleArn present but role lacks `lambda:InvokeFunction` | Role identity-based policy missing the permission. |
| Cross-account Lambda, role has permission but target lacks resource-based policy | Both sides must allow for cross-account. Add the resource-based policy statement. |
| SourceArn condition mismatch | The condition's ArnLike pattern does not match the actual rule ARN (e.g., wrong bus name in the ARN). |
| Multiple rules targeting same Lambda | Each rule needs its own `add-permission` statement (or a wildcard SourceArn, which is less secure). |

## Bus mismatch patterns table (moved from SKILL.md)

Common bus mismatch patterns:

| Rule EventBusName | PutEvents EventBusName | Result |
|---|---|---|
| `custom.orders` | `default` (or omitted) | No match — events on default bus, rule on custom |
| `default` | `custom.orders` | No match — events on custom bus, rule on default |
| `custom.orders` | `custom.orders` | Correct — same bus |

## Deep reference: EventBridge rule-firing layer model (moved from SKILL.md)

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

## Recent AWS features (2024-2026) (moved from SKILL.md)

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
