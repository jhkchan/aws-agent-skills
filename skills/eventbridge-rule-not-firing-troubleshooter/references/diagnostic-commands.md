# EventBridge Rule Not Firing Troubleshooter — diagnostic commands (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## Account-wide pre-flight commands (moved from SKILL.md)

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

## Rule-state short-circuit (moved from SKILL.md)

| `State` | Effect on diagnosis |
|---|---|
| `ENABLED` | Proceed with pattern/bus/target diagnosis. |
| `DISABLED` | The rule was manually disabled OR EventBridge auto-disabled it after a schedule expression syntax error. Check `ScheduleExpression` for syntax errors; re-enable with `enable-rule`. |
| `ENABLED` with `ManagedBy: [SVC]` | AWS service-managed rule (e.g., CloudWatch Alarm → SNS). Do not modify directly; the owning service controls state. |

## Bus existence check (moved from SKILL.md)

```bash
aws events list-event-buses --name-prefix <bus-name> --output json
```

## Step 2a: test-event-pattern probe (moved from SKILL.md)

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

## Step 2a: result interpretation (moved from SKILL.md)

If `Result: false`, the pattern does not match. Proceed to 2b to
identify which field mismatches.

If `Result: true`, the pattern matches — the issue is downstream (bus
mismatch, target permissions, DLQ). Proceed to Steps 5-8.

## Step 3: schedule expression gate (moved from SKILL.md)

Symptom: a schedule-based rule (no EventPattern, has
ScheduleExpression) never fires at the expected time, or the rule's
State is DISABLED.

```bash
aws events describe-rule \
  --name <rule-name> --event-bus-name <bus-name> \
  --output json | jq '{ScheduleExpression, State}'
```

## Step 4a: DLQ inspection commands (moved from SKILL.md)

```bash
# For SQS DLQ:
aws sqs receive-message --queue-url <dlq-url> \
  --max-number-of-messages 5 --output json

# Extract the errorMessage field from each message body
aws sqs receive-message --queue-url <dlq-url> \
  --max-number-of-messages 5 --output json | \
  jq '.Messages[].Body | fromjson | .errorMessage // .'
```

## Step 4b: input transformer inspection (moved from SKILL.md)

```bash
aws events describe-rule \
  --name <rule-name> --event-bus-name <bus-name> \
  --output json | jq '.Targets[0].InputTransformer'
```

## Step 5a: rule IAM role check (moved from SKILL.md)

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

## Step 5a: verdict and same-account note (moved from SKILL.md)

If `implicitDeny`, the role lacks `lambda:InvokeFunction` on the target.
**ROOT_CAUSE_IDENTIFIED**, `LAYER: TARGET_IAM_ROLE`.

For same-account targets, EventBridge uses a service-linked role and
does NOT require a RoleArn on the rule. The target's resource-based
policy is the gate.

## Step 5b: Lambda resource-based policy probe (moved from SKILL.md)

```bash
aws lambda get-policy --function-name <target-lambda> --output json 2>/dev/null
```

## Step 5b: required policy statement and fix (moved from SKILL.md)

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

## Step 6: EventBus policy probe and cross-account example (moved from SKILL.md)

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

## Step 6 fix: put-event-bus-policy (moved from SKILL.md)

Fix:

```bash
aws events put-event-bus-policy \
  --event-bus-name <bus-name> \
  --policy '<json-policy>' --output json
```

## Step 7: input transformer inspection (moved from SKILL.md)

```bash
aws events describe-rule \
  --name <rule-name> --event-bus-name <bus-name> \
  --output json | jq '.Targets[0].InputTransformer, .Targets[0].InputPath'
```

## Step 8: bus mismatch probes (moved from SKILL.md)

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

## Step 9: event source mapping probe (moved from SKILL.md)

```bash
aws lambda get-event-source-mapping \
  --function-name <lambda-name> --output json 2>/dev/null
```

## Step 9: mapping checklist (moved from SKILL.md)

Check:
- `State: Enabled` — the mapping is active.
- `BatchSize` — reasonable for the throughput.
- `StartingPosition: LATEST` vs `TRIM_HORIZON` — LATEST skips old
  records; TRIM_HORIZON reads from the earliest available.
- `FunctionResponseTypes: [ReportBatchItemFailures]` — enables
  partial batch failure reporting.

If the mapping is disabled or misconfigured, the Lambda never receives
records regardless of the EventBridge rule configuration.

## Step 11: verification command (moved from SKILL.md)

After identifying the likely root cause and proposing a fix, always
verify the corrected pattern:

```bash
aws events test-event-pattern \
  --event-pattern '<corrected-pattern-json>' \
  --event '<sample-event-json>' --output json
```

`Result: true` confirms the corrected pattern matches. Only then
update the rule.

## Pre-flight safety checks (moved from SKILL.md)

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
