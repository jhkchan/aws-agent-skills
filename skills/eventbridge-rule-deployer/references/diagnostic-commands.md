# Diagnostic Commands

Blocks moved verbatim from SKILL.md in the agentskills.io progressive-disclosure
restructure. No content changed; load when a SKILL.md pointer stub applies.

## Pre-flight data requirements (moved from SKILL.md)

| Input | Source | Why |
|---|---|---|
| Event source (for pattern rules) | Service docs / `events list-event-sources` | Drives the `source` field |
| Detail-type | Service docs | Drives the `detail-type` filter |
| Sample event payload | `PutEvents` test or `TestEventPattern` | Validates the pattern matches before deploy |
| Target type and ARN | Application config / `aws lambda list-functions` etc. | Determines target config |
| Region(s) | Single-region vs multi-region | Drives global-endpoint decision |
| Existing rules on the bus | `aws events list-rules --event-bus-name <bus>` | Detect name collisions and rule-graph cycles |
| Cross-account producer account IDs | `aws organizations list-accounts` or stated input | Required for bus policy |
| Existing DLQs | `aws sqs list-queues --queue-name-prefix eventbridge-` | Reuse vs create |

## Step 1: Pattern / schedule / rate rule CLI examples (moved from SKILL.md)

**Pattern rule** — triggered by matching events:

```bash
aws events put-rule \
  --name guardduty-high-severity \
  --event-bus-name default \
  --event-pattern '{"source":["aws.guardduty"],"detail-type":["GuardDuty Finding"],"detail":{"severity":[{"numeric":[">=",7]}]}}' \
  --state ENABLED \
  --description "Match GuardDuty severity >= 7"
```

**Schedule rule** — cron-based (legacy path; prefer Scheduler):

```bash
aws events put-rule \
  --name nightly-backup \
  --schedule-expression 'cron(0 2 * * ? *)' \
  --state ENABLED \
  --description "Run nightly at 02:00 UTC"
```

**Rate rule** — fixed interval:

```bash
aws events put-rule \
  --name healthcheck-every-5-min \
  --schedule-expression 'rate(5 minutes)' \
  --state ENABLED
```

## Step 2: Pattern validation CLI (moved from SKILL.md)

Validate before deploying:

```bash
aws events test-event-pattern \
  --event-pattern file://pattern.json \
  --event file://sample-event.json
```

## Step 3: Target wiring and invocation-permission CLI (moved from SKILL.md)

```bash
aws events put-targets \
  --rule <rule-name> \
  --event-bus-name <bus> \
  --targets '[{"Id":"lambda-target","Arn":"arn:aws:lambda:us-east-1:111111111111:function:my-fn","DeadLetterConfig":{"Arn":"arn:aws:sqs:us-east-1:111111111111:eventbridge-my-rule-dlq"},"RetryPolicy":{"MaximumRetryAttempts":3,"MaximumEventAgeInSeconds":900}}]'
```

For Lambda targets, grant EventBridge permission to invoke:

```bash
aws lambda add-permission \
  --function-name my-fn \
  --statement-id EventBridgeInvoke-<rule-name> \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-1:111111111111:rule/<bus>/<rule-name> \
  --source-account 111111111111
```

A missing invocation permission produces silent non-delivery. Verify
after wiring:

```bash
aws lambda get-policy --function-name my-fn --query 'Policy' --output text \
  | jq '.Statement[] | select(.Principal.Service=="events.amazonaws.com")'
```

## Step 4: DLQ create/attach and alarm CLI (moved from SKILL.md)

```bash
aws sqs create-queue --queue-name eventbridge-<rule>-dlq
aws sqs set-queue-attributes \
  --queue-url https://sqs.<region>.amazonaws.com/<account>/eventbridge-<rule>-dlq \
  --attributes MessageRetentionPeriod=1209600
aws events put-targets \
  --rule <rule> --event-bus-name <bus> \
  --targets '[{"Id":"<target-id>","Arn":"<target-arn>","DeadLetterConfig":{"Arn":"arn:aws:sqs:<region>:<account>:eventbridge-<rule>-dlq"},"RetryPolicy":{"MaximumRetryAttempts":3,"MaximumEventAgeInSeconds":900}}]'
```

CloudWatch alarm on DLQ depth (non-negotiable for production):

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name EventBridge-<rule>-DLQ-Depth \
  --metric-name ApproximateNumberOfMessagesVisible \
  --namespace AWS/SQS \
  --statistic Sum --period 60 --evaluation-periods 1 \
  --threshold 0 --comparison-operator GreaterThanThreshold \
  --dimensions Name=QueueName,Values=eventbridge-<rule>-dlq \
  --alarm-actions <sns-arn>
```

## Step 5: Input transformer CLI (moved from SKILL.md)

```bash
aws events put-targets \
  --rule <rule> --event-bus-name <bus> \
  --targets '[{
    "Id":"lambda-target",
    "Arn":"arn:aws:lambda:us-east-1:111111111111:function:my-fn",
    "InputTransformer":{
      "InputPathsMap":{
        "user":"$.detail.user",
        "event_time":"$.time",
        "source":"$.source"
      },
      "InputTemplate":"{\"event_type\":\"eventbridge-trigger\",\"user\":<user>,\"triggered_at\":\"<event_time>\",\"origin\":\"<source>\"}"
    }
  }]'
```

## Step 6: Cross-account event routing CLI (moved from SKILL.md)

Cross-account events require TWO configurations:

1. **Receiving bus resource policy** grants the producing account
   `events:PutEvents` permission:

```bash
aws events put-permission \
  --event-bus-name <receiving-bus> \
  --action events:PutEvents \
  --principal <producer-account-id> \
  --statement-id AllowProducerAccount-<id> \
  --condition '{"Type":"StringEquals","Key":"aws:SourceAccount","Value":"<producer-account-id>"}'
```

2. **Producer calls PutEvents with the receiving bus ARN:**

```bash
aws events put-events \
  --entries '[{"EventBusName":"arn:aws:events:us-east-1:<receiver-account>:event-bus/<receiving-bus>","Source":"my.app","DetailType":"order.created","Detail":"{\"order_id\":\"ord-123\"}"}]'
```

For organization-wide routing (all accounts in an Organization):

```bash
aws events put-permission \
  --event-bus-name <receiving-bus> \
  --action events:PutEvents \
  --principal "*" \
  --statement-id AllowOrg \
  --condition '{"Type":"StringEquals","Key":"aws:PrincipalOrgID","Value":"o-xxxxxxxxxx"}'
```

**Cross-account security rule:** prefer `aws:SourceAccount` or
`aws:PrincipalOrgID` over `aws:SourceIp` — IP-based restrictions are
bypassable.

## Step 8: Archive and replay CLI (moved from SKILL.md)

Archives capture events for debugging and replay. Create on a bus:

```bash
aws events create-archive \
  --name app-events-archive \
  --event-source-arn arn:aws:events:us-east-1:111111111111:event-bus/app-events \
  --retention 7 \
  --event-pattern '{"source":["my.app"]}'
```

Replay a specific time range:

```bash
aws events start-replay \
  --name debug-2026-08-incident \
  --event-source-arn arn:aws:events:us-east-1:111111111111:event-bus/app-events \
  --event-start-time 2026-08-04T00:00:00Z \
  --event-end-time 2026-08-04T06:00:00Z \
  --destination '{"Arn":"arn:aws:events:us-east-1:111111111111:event-bus/app-events"}'
```

**Critical warnings:**
- Replay re-publishes events to ALL rules matching the archive
  pattern, including rules created AFTER the original events. Pause
  new rules before replaying.
- Archives are NOT backups — they are operational tools. For
  compliance retention, use S3 with lifecycle policies.
- Archives bill per-event-month. A high-volume bus with 90-day
  retention is a significant line item. Default to 7-30 days.

## Step 10: Global endpoints CLI (moved from SKILL.md)

For multi-region failover:

```bash
aws events create-endpoint \
  --name orders-failover \
  --routing-config '{"FailoverConfig":{"Primary":{"HealthCheck":"arn:aws:route53:...:healthcheck/primary"},"Secondary":{"RouteDetails":{"HealthCheck":"arn:aws:route53:...:healthcheck/secondary"}}}}' \
  --event-buses '[{"EventBusArn":"arn:aws:events:us-east-1:111111111111:event-bus/orders"},{"EventBusArn":"arn:aws:events:us-west-2:111111111111:event-bus/orders"}]' \
  --replication-config '{"State":"ENABLED"}'
```

Requirements:
- Both buses must have equivalent rules and targets
- Both buses must have equivalent bus policies, DLQs, KMS keys
- Schema Registry and archives are per-region — replicate separately
- Producers target the endpoint ARN, not a regional bus ARN
- Failover is driven by Route53 health checks; replication is
  asynchronous (a few seconds of lag during failover)

## Step 11: Schema Registry CLI (moved from SKILL.md)

```bash
aws schemas create-registry \
  --registry-name app-events-schemas \
  --description "Discovered schemas for app-events bus"

aws schemas create-discoverer \
  --discoverer-name app-events-discoverer \
  --source-arn arn:aws:events:us-east-1:111111111111:event-bus/app-events \
  --description "Auto-discover schemas from app-events bus"
```

Notes:
- Auto-discovery captures schemas ONLY on the default bus by default
- Custom-bus schema discovery must be explicitly enabled via
  `create-discoverer`
- Code bindings (Java, Python, TypeScript) can be generated from
  discovered schemas for type-safe event publishing/consumption
- Do NOT enable schema discovery on a bus with untrusted publishers —
  attacker-crafted events pollute the registry

## Step 12: Deployment verification commands (moved from SKILL.md)

```bash
# 1. Rule exists and is ENABLED
aws events describe-rule --name <rule> --event-bus-name <bus> \
  --query '[Name, State, EventPattern, ScheduleExpression]'

# 2. Targets wired with DLQ and retry
aws events list-targets-by-rule --rule <rule> --event-bus-name <bus>

# 3. Lambda invocation permission
aws lambda get-policy --function-name <fn> --query 'Policy' --output text \
  | jq '.Statement[] | select(.Principal.Service=="events.amazonaws.com")'

# 4. DLQ exists and depth is zero
aws sqs get-queue-url --queue-name eventbridge-<rule>-dlq
aws sqs get-queue-attributes \
  --queue-url https://sqs.<region>.amazonaws.com/<account>/eventbridge-<rule>-dlq \
  --attribute-names ApproximateNumberOfMessagesVisible

# 5. Bus policy for cross-account (if applicable)
aws events describe-event-bus --name <bus> --query 'Policy'

# 6. Archive configured (if used)
aws events describe-archive --archive-name <archive>

# 7. Test the pattern against a fresh sample
aws events test-event-pattern \
  --event-pattern file://pattern.json --event file://sample-event.json

# 8. CloudWatch metrics post-deploy
aws cloudwatch get-metric-statistics \
  --namespace AWS/Events \
  --metric-name Invocations \
  --dimensions Name=RuleName,Values=<rule> \
  --start-time $(date -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date +%Y-%m-%dT%H:%M:%S) --period 300 --statistics Sum

# 9. TriggeredInvocations vs FailedInvocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Events \
  --metric-name FailedInvocations \
  --dimensions Name=RuleName,Values=<rule> \
  --start-time $(date -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date +%Y-%m-%dT%H:%M:%S) --period 300 --statistics Sum
```
