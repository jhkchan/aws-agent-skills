# EventBridge Schedule and Permissions Reference Guide

Supplementary reference for the EventBridge Rule Not Firing
Troubleshooter skill. Loaded on-demand when a diagnostic needs cron/rate
expression syntax, cross-account target permission patterns, EventBus
policy structure, or event source mapping semantics.

## Cron expressions (6 fields)

EventBridge cron requires exactly 6 fields:

```
cron(Minutes Hours Day-of-month Month Day-of-week Year)
```

| Field | Values | Wildcards | Notes |
|---|---|---|---|
| Minutes | 0-59 | `,` `-` `*` `/` | — |
| Hours | 0-23 | `,` `-` `*` `/` | — |
| Day-of-month | 1-31 | `,` `-` `*` `/` `?` `L` `W` | `?` = no specific value; `L` = last day; `W` = nearest weekday |
| Month | 1-12 or JAN-DEC | `,` `-` `*` `/` | — |
| Day-of-week | 1-7 or SUN-SAT | `,` `-` `*` `/` `?` `L` `#` | `?` = no specific value; `L` = last occurrence; `#` = nth occurrence |
| Year | 1970-2199 | `,` `-` `*` `/` | — |

### Day-of-month and Day-of-week mutual exclusion

One of these two fields MUST be `?` (no specific value). Using `*` in
both is invalid and auto-disables the rule.

```
cron(0 9 * * ? *)    ← valid (every day at 09:00 UTC)
cron(0 9 ? * MON *)  ← valid (every Monday at 09:00 UTC)
cron(0 9 * * * *)    ← INVALID (both are *)
```

### Common cron expressions

| Expression | Meaning |
|---|---|
| `cron(0 9 * * ? *)` | Daily at 09:00 UTC |
| `cron(0 18 ? * MON-FRI *)` | Weekdays at 18:00 UTC |
| `cron(0 0 1 * ? *)` | First of every month at 00:00 UTC |
| `cron(0 0 L * ? *)` | Last day of every month at 00:00 UTC |
| `cron(0 0 ? * SUN#2 *)` | Second Sunday of every month at 00:00 UTC |
| `cron(0/15 * * * ? *)` | Every 15 minutes |
| `cron(0 9 1 1,4,7,10 ? *)` | First of Jan, Apr, Jul, Oct at 09:00 UTC |

### Cron pitfalls

| Expression | Error | Fix |
|---|---|---|
| `cron(0 9 * * *)` | 5 fields (missing Year) | Add year: `cron(0 9 * * ? *)` |
| `cron(0 9 * * * *)` | Both day fields are `*` | Use `?` in one: `cron(0 9 * * ? *)` |
| `cron(0 9 31 2 * *)` | Feb 31 does not exist | Use valid date |
| `cron(0 25 * * ? *)` | Hour 25 invalid | Hours range is 0-23 |

## Rate expressions

```
rate(value unit)
```

- value: positive integer (>= 1)
- unit: `minute(s)`, `hour(s)`, `day(s)`
- singular: `rate(1 minute)` (value = 1)
- plural: `rate(5 minutes)` (value > 1)

| Expression | Meaning |
|---|---|
| `rate(1 minute)` | Every minute |
| `rate(5 minutes)` | Every 5 minutes |
| `rate(1 hour)` | Every hour |
| `rate(1 day)` | Every day at the same time |

**Important:** Rate expressions do NOT support seconds, weeks, or months.
Minimum is `rate(1 minute)`.

## Timezone

EventBridge cron and rate expressions use **UTC only**. There is no
timezone parameter. A cron expression `cron(0 9 * * ? *)` fires at
09:00 UTC regardless of the account's default region.

## Schedule auto-disable behavior

EventBridge silently auto-disables rules (State: DISABLED) when:
1. The ScheduleExpression has a syntax error (wrong number of fields,
   invalid wildcards, impossible date).
2. (Rare) Sustained target invocation failure for some target types.

Auto-disabled rules do NOT emit an error event. The operator discovers
the disable via `describe-rule` showing `State: DISABLED`.

**Fix:** Correct the ScheduleExpression syntax, then call `enable-rule`.

## Target Lambda resource-based policy

For EventBridge to invoke a Lambda function, the Lambda's resource-based
policy MUST include a statement allowing `lambda:InvokeFunction` for the
`events.amazonaws.com` principal:

```json
{
  "Effect": "Allow",
  "Principal": {"Service": "events.amazonaws.com"},
  "Action": "lambda:InvokeFunction",
  "Condition": {
    "ArnLike": {
      "AWS:SourceArn": "arn:aws:events:us-east-1:111111111111:rule/<bus-name>/<rule-name>"
    }
  },
  "Resource": "arn:aws:lambda:us-east-1:111111111111:function:<function-name>"
}
```

Add via CLI:

```bash
aws lambda add-permission \
  --function-name <lambda-name> \
  --statement-id EventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:<region>:<account>:rule/<bus>/<rule-name>
```

### Same-account vs cross-account

| Scenario | What's needed |
|---|---|
| Same-account Lambda | Lambda resource-based policy with `events.amazonaws.com` principal. No RoleArn on the rule. |
| Cross-account Lambda | Lambda resource-based policy AND rule's RoleArn with `lambda:InvokeFunction` on the target. |
| Same-account API Gateway | API Gateway resource policy and EventBridge role with `apigateway:POST` permission. |
| Same-account SNS | SNS topic policy allowing `events.amazonaws.com` principal. |
| Same-account SQS | SQS queue policy allowing `events.amazonaws.com` principal. |
| Same-account Step Functions | Step Functions state machine policy allowing `events.amazonaws.com` principal. |

## EventBus policy for cross-account PutEvents

For account B to put events on a bus in account A:

Account A's bus policy MUST grant `events:PutEvents`:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::<account-b>:root"},
    "Action": "events:PutEvents",
    "Resource": "arn:aws:events:<region>:<account-a>:event-bus/<bus-name>"
  }]
}
```

Apply via CLI:

```bash
aws events put-event-bus-policy \
  --event-bus-name <bus-name> \
  --policy '<json-policy>'
```

For same-account PutEvents, no policy is needed — the account has
implicit access.

## Input transformer reference

Input transformers reshape the event before delivering it to the target.

```json
{
  "InputPathsMap": {
    "order_id": "$.detail.orderId",
    "status": "$.detail.status",
    "source": "$.source"
  },
  "InputTemplate": "{\"orderId\": \"<order_id>\", \"status\": \"<status>\", \"origin\": \"<source>\"}"
}
```

Rules:
- Every `<variable>` in `InputTemplate` MUST have a mapping in
  `InputPathsMap`.
- If a JSON path in `InputPathsMap` does not exist in the event, the
  transformation fails.
- Failed transformations send the original event to the DLQ (if
  configured) with an `errorMessage` field.
- The template MUST produce valid JSON for JSON-expecting targets
  (Lambda, Step Functions).
- For Lambda targets, the template output becomes the event payload.

## Event source mapping vs EventBridge rule

An EventBridge rule triggering a Lambda is one delivery path. A Lambda
reading from Kinesis/DynamoDB Streams via an event source mapping is an
entirely separate path.

| Path | Configuration | Diagnosis |
|---|---|---|
| EventBridge → Lambda | EventBridge rule with Lambda target | `describe-rule`, `test-event-pattern`, `get-policy` |
| Kinesis → Lambda (ESM) | Lambda event source mapping | `get-event-source-mapping` |
| DynamoDB Streams → Lambda (ESM) | Lambda event source mapping | `get-event-source-mapping` |
| SQS → Lambda (ESM) | Lambda event source mapping | `get-event-source-mapping` |

If the event source is Kinesis/Stream, EventBridge is NOT the delivery
mechanism. Diagnose the event source mapping, not the EventBridge rule.
