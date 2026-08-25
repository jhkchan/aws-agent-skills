# EventBridge Rule Not Firing Troubleshooter — error handling (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## DLQ errorMessage mapping (moved from SKILL.md)

The `errorMessage` field in the DLQ message body identifies the failure
reason:

| errorMessage pattern | Cause | Layer |
|---|---|---|
| `"InputTemplate is invalid"` or `"Invalid template"` | Input transformer template has a syntax error | INPUT_TRANSFORMER_ERROR |
| `"Path ... is not present"` | Input transformer references a JSON path absent from the event | INPUT_TRANSFORMER_ERROR |
| `"ResourceArn"` or `"AccessDenied"` | Target invocation denied (permissions) | TARGET_IAM_ROLE / TARGET_LAMBDA_PERMISSION |
| No errorMessage, event body present | Rule matched, target invocation failed at the target side | Depends on target-side probe |

## Input transformer rules and error table (moved from SKILL.md)

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

## Remediation guidance — per-verdict fixes (moved from SKILL.md)

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
