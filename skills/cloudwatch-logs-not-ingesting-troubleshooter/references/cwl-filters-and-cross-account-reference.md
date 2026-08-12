# CloudWatch Logs Filters, Subscription, and Cross-Account Reference Guide

Supplementary reference for the CloudWatch Logs Not-Ingesting
Troubleshooter skill. Loaded on-demand when a diagnostic needs
subscription-filter concurrency semantics, metric-filter pattern
syntax, cross-account delivery configuration, or retention policy
behaviour.

## Subscription filters

A subscription filter on a log group forwards matching events to a
destination (Lambda, Kinesis Data Streams, or Firehose). Each log
group supports up to 2 subscription filters.

### Destination types

| Destination | Throughput | IAM requirement |
|---|---|---|
| Lambda | Up to 2x the account's `ConcurrentExecutions` quota for subscription deliveries | The Lambda resource policy must allow `logs:Invoke` from `logs.<region>.amazonaws.com` |
| Kinesis Data Streams | Higher throughput; shard-scaled | The stream resource policy must allow `kinesis:PutRecord` from the logs service principal |
| Firehose | Buffered delivery to S3 / OpenSearch / etc. | The Firehose delivery stream's role must allow the logs service principal to write |

### Concurrency budget for Lambda destinations

Subscription deliveries to Lambda are capped at **2x the account's
`ConcurrentExecutions` quota**. This is a per-account budget shared
across ALL subscription filters in the account, not per-filter.

| Scenario | Effect |
|---|---|
| 1 subscription filter, low volume | No issue; the destination Lambda processes batches well within budget |
| 3 subscription filters, each moderate volume | Combined fan-out may approach the 2x budget under load |
| Sustained high volume across multiple filters | The budget is exhausted; batches are silently dropped (no error surfaced to the source application) |

### Diagnosing subscription-filter drops

```bash
# Confirm the subscription filter is active
aws logs describe-subscription-filters --log-group-name <group> --output json

# Compare IncomingLogEvents vs Lambda Invocations
aws cloudwatch get-metric-statistics --namespace AWS/Logs \
  --metric-name IncomingLogEvents \
  --dimensions Name=LogGroupName,Value=<group> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --output json

aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=<dest-function> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --output json

# Check the destination's concurrency utilisation
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name ConcurrentExecutions \
  --dimensions Name=FunctionName,Value=<dest-function> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Maximum --output json

aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Throttles \
  --dimensions Name=FunctionName,Value=<dest-function> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --output json
```

If `IncomingLogEvents` exceeds Lambda `Invocations` and the
destination's `ConcurrentExecutions` is at the account limit,
subscription batches are being dropped.

### Remediation options

| Option | Effect |
|---|---|
| Reserved concurrency on the destination Lambda | Guarantees the destination gets capacity up to the reserved amount |
| Reduce fan-out | Consolidate or filter at the source to lower invocation rate |
| Switch destination to Kinesis | Higher throughput; shard-scaled (no Lambda concurrency cap) |
| Request a concurrency quota increase | Raises the 2x budget account-wide |

## Metric filter pattern syntax

Metric filters test the `message` field of each log event and emit a
metric data point when the pattern matches.

### Pattern types

| Pattern type | Example | Matches |
|---|---|---|
| Term (space-delimited) | `ERROR` | Any event whose message contains the literal `ERROR` (case-sensitive) |
| Quoted phrase | `"internal error"` | Any event containing the exact phrase `internal error` |
| JSON field | `{ $.status = 500 }` | Events whose message is valid JSON with `status` equal to `500` |
| JSON nested | `{ $.response.statusCode = 500 }` | Events whose message is JSON with a nested `response.statusCode` |
| Inequality | `{ $.latency > 1000 }` | Events whose JSON `latency` field exceeds 1000 |
| Exists | `{ $.userId = "*" }` | Events whose JSON has a `userId` field of any value |

### Common metric-filter footguns

| Pattern | Issue |
|---|---|
| `{ $.status = 500 }` on text-formatted logs | The pattern expects JSON; text logs produce zero matches |
| `[ERROR]` (term) on JSON-formatted logs | The term search treats the JSON as a string; may match on field names by accident |
| Unbalanced quotes / brackets | The filter is rejected at creation but may silently produce zero points if the validation is bypassed |
| Wrong `metricNamespace` | The metric is emitted to a different namespace than the alarm queries |
| `metricValue` is a string literal `"1"` instead of the JSON field | The metric always increments by 1, ignoring the JSON field value |
| Default `defaultValue: 0` hides gaps | When no events match in a period, the metric emits 0; the alarm threshold must account for this |

### Testing a metric filter pattern

```bash
# Test the pattern against actual events
aws logs filter-log-events --log-group-name <group> \
  --filter-pattern '{ $.status = 500 }' \
  --start-time $(date -d '-1 hour' +%s)000 --output json | \
  jq '.events | length'
```

If `filter-log-events` returns matches but the metric alarm is not
firing, the issue is the metric filter's `metricTransformations`
(namespace, value, or default value), not the pattern itself.

## Cross-account log delivery

Cross-account delivery routes log events from a source account to a
destination account's log group. The destination-side resource policy
is the gating side.

### Pattern 1: Cross-account subscription via destination

This is the standard pattern for centralised log aggregation.

**Destination account (111111111111):**

```bash
# 1. Create a CloudWatch Logs destination
aws logs put-destination \
  --destination-name CrossAccountDest \
  --target-arn arn:aws:logs:us-east-1:111111111111:log-group:/centralised/app \
  --role-arn arn:aws:iam::111111111111:role/CWLDestinationRole \
  --region us-east-1 --output json

# 2. Attach an access policy granting the source account
aws logs put-destination-policy \
  --destination-name CrossAccountDest \
  --access-policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::222222222222:root"},
      "Action": "logs:PutSubscriptionFilter",
      "Resource": "arn:aws:logs:us-east-1:111111111111:destination:CrossAccountDest"
    }]
  }' --region us-east-1
```

**Source account (222222222222):**

```bash
# 3. Create a subscription filter pointing to the destination
aws logs put-subscription-filter \
  --log-group-name /app/source \
  --filter-name ForwardToCentral \
  --filter-pattern "" \
  --destination-arn arn:aws:logs:us-east-1:111111111111:destination:CrossAccountDest \
  --region us-east-1 --output json
```

### Pattern 2: Resource-based policy on the destination log group

For direct PutLogEvents cross-account (less common), the destination
log group's resource policy must grant the source account
`logs:PutLogEvents`.

```bash
aws logs put-resource-policy \
  --policy-name AllowCrossAccount222222 \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::222222222222:root"},
      "Action": ["logs:PutLogEvents", "logs:CreateLogStream"],
      "Resource": "arn:aws:logs:us-east-1:111111111111:log-group:/cross-account/*"
    }]
  }' --profile 111111-profile
```

### Common cross-account footguns

| Pattern | Cause |
|---|---|
| Source IAM allows `logs:PutLogEvents`, delivery still fails | Destination resource policy is missing — it is the gating side |
| Destination role lacks trust policy for `logs.amazonaws.com` | The logs service cannot assume the delivery role |
| Wrong region in the destination ARN | CloudWatch Logs destinations are regional; a cross-region delivery needs a separate destination per region |
| Subscription filter distribution not applied | The destination's access policy must use `logs:PutSubscriptionFilter`, not `logs:PutLogEvents` |

## Retention policy behaviour

| `retentionInDays` | Effect |
|---|---|
| Not set (default) | Logs are retained indefinitely (`Never expire`) |
| 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653 | Streams older than the window are deleted |

### Retention footguns

| Pattern | Cause |
|---|---|
| Retention lowered from `Never expire` to `7 days` | All streams older than 7 days are deleted within minutes; not recoverable |
| Tag-based automation changed retention | An SCP or tag policy automation may have lowered retention without the operator's knowledge |
| Retention-driven deletions produce no CloudTrail event | The deletion is internal; operators who "see no DeleteLogStream event" are on the wrong diagnostic branch |
| CMK-encrypted log group with short retention | KMS Decrypt charges continue for the window; retention affects storage, not encryption |

### Changing retention

```bash
# Raise retention (safe — does not delete any streams)
aws logs put-retention-policy --log-group-name <group> \
  --retention-in-days 90 --profile <p>

# Lower retention (destructive — streams older than the new window
# are deleted; ALWAYS confirm before lowering)
aws logs put-retention-policy --log-group-name <group> \
  --retention-in-days 7 --profile <p>
```

Expired logs are not recoverable. Always raise first; lower only
after explicit operator confirmation.

## KMS encryption for log groups

| `encryptionType` | Key | Caller KMS permission |
|---|---|---|
| (default, no `kmsKeyId`) | CloudWatch-managed key | None |
| `kmsKeyId: <cmk>` | Customer-managed CMK | Emitter: `kms:GenerateDataKey`; reader: `kms:Decrypt` |

The key policy must also grant the CloudWatch Logs service principal
(`logs.<region>.amazonaws.com`) the following on the key:

- `kms:Encrypt`
- `kms:Decrypt`
- `kms:ReEncrypt*`
- `kms:GenerateDataKey*`
- `kms:DescribeKey`
- `kms:CreateGrant`

Without the key-policy side, CloudWatch Logs cannot encrypt/decrypt
on the caller's behalf even if the caller's IAM policy allows the KMS
actions. `AssociateKmsKey` must run at log-group creation or before
the first write; existing events remain under the prior key.
