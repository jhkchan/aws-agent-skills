# Diagnostic Commands

Blocks moved verbatim from SKILL.md in the agentskills.io progressive-disclosure
restructure. No content changed; load when a SKILL.md pointer stub applies.

## Step 3: Target wiring CLI (moved from SKILL.md)

```bash
aws events put-targets \
  --rule <rule-name> \
  --event-bus-name <bus> \
  --targets '[{"Id":"lambda-target","Arn":"arn:aws:lambda:us-east-1:111111111111:function:my-fn","DeadLetterConfig":{"Arn":"arn:aws:sqs:us-east-1:111111111111:my-dlq"},"RetryPolicy":{"MaximumRetryAttempts":3,"MaximumEventAgeInSeconds":900}}]'
```

For Lambda targets, also grant EventBridge permission to invoke:

```bash
aws lambda add-permission \
  --function-name my-fn \
  --statement-id EventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-1:111111111111:rule/<rule-name>
```

## Step 10: Audit and verify commands (moved from SKILL.md)

```bash
# 1. Rule exists and is ENABLED
aws events describe-rule --name <rule> --event-bus-name <bus> \
  --query '[Name, State, EventPattern]'

# 2. Targets wired with DLQ and retry
aws events list-targets-by-rule --rule <rule> --event-bus-name <bus>

# 3. Lambda invocation permission
aws lambda get-policy --function-name <fn> \
  --query 'Policy' --output text | jq '.Statement[] | select(.Principal.Service=="events.amazonaws.com")'

# 4. DLQ depth
aws sqs get-queue-attributes \
  --queue-url https://sqs.<region>.amazonaws.com/<account>/<dlq> \
  --attribute-names ApproximateNumberOfMessagesVisible

# 5. Recent invocations (CloudTrail)
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=InvokeFunction \
  --start-time $(date -v-1H +%Y-%m-%dT%H:%M:%S) --end-time $(date +%Y-%m-%dT%H:%M:%S)

# 6. Test the pattern against a fresh sample
aws events test-event-pattern \
  --event-pattern file://pattern.json --event file://sample-event.json
```

For replay capability, verify an archive exists:

```bash
aws events describe-archive --archive-name <archive>
```

For schema discovery:

```bash
aws schemas describe-registry --registry-name <bus>-schemas
```
