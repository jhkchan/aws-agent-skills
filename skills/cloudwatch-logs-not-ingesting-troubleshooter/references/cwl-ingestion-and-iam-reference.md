# CloudWatch Logs Ingestion and IAM Reference Guide

Supplementary reference for the CloudWatch Logs Not-Ingesting
Troubleshooter skill. Loaded on-demand when a diagnostic needs
PutLogEvents sequence-token semantics, IAM action matrices, Lambda
auto-create rules, or data-protection policy patterns.

## PutLogEvents sequence token semantics

Each PutLogEvents call (after the first to a given log stream) must
include the `sequenceToken` returned by the previous successful call
to the same log stream. The token serialises writes within a single
stream.

### Token sources

| Source | When |
|---|---|
| Previous PutLogEvents response `nextSequenceToken` | The standard source for sequential writes by one emitter |
| `DescribeLogStreams` `uploadSequenceToken` | The current expected token (read this after a restart or a gap) |
| Absent on the very first call to a new stream | The first PutLogEvents call omits `sequenceToken`; CloudWatch creates the stream if `logs:CreateLogStream` is allowed |

### Collision patterns

| Pattern | Symptom |
|---|---|
| Two emitters writing to the same stream concurrently | Each sees the other's token as stale; both get `InvalidSequenceTokenException` on roughly half of calls |
| Emitter caches the token across calls | After the first call, the cached token is stale; every subsequent call fails |
| Emitter retries after a transient error | The retry uses the old token; the original call may have succeeded and advanced the token |
| Lambda function writes from multiple concurrent invocations to the same stream | Invocations collide on the token; use the Lambda runtime's built-in log API instead of direct PutLogEvents |

### Error responses

| Error | Meaning |
|---|---|
| `InvalidSequenceTokenException` | The token does not match the stream's current `uploadSequenceToken`. The error message includes the expected token. |
| `DataAlreadyAcceptedException` | The events were already ingested (the prior call succeeded). The response includes the correct `nextSequenceToken`; use it for the next call. |

## IAM action matrix for CloudWatch Logs

### Write path (application / agent / Lambda)

| Action | When | Resource scope |
|---|---|---|
| `logs:CreateLogGroup` | First-ever write to a new log group (Lambda auto-create needs this) | `arn:aws:logs:<region>:<account>:log-group:<group>` or `*` |
| `logs:CreateLogStream` | First write to a new log stream | `arn:aws:logs:<region>:<account>:log-group:<group>:*` |
| `logs:PutLogEvents` | Every batch of events | `arn:aws:logs:<region>:<account>:log-group:<group>:*` or `arn:aws:logs:<region>:<account>:log-group:<group>:stream:<stream>` |
| `logs:DescribeLogStreams` | Some SDKs call this before PutLogEvents to find the stream | `arn:aws:logs:<region>:<account>:log-group:<group>:*` |

### Read path (analyst / Insights / SIEM pull)

| Action | When |
|---|---|
| `logs:DescribeLogGroups` | List log groups |
| `logs:DescribeLogStreams` | List streams within a group |
| `logs:GetLogEvents` | Read events from a stream |
| `logs:FilterLogEvents` | Query events across streams |
| `logs:StartQuery` / `logs:GetQueryResults` | CloudWatch Logs Insights |
| `logs:DescribeMetricFilters` / `logs:DescribeSubscriptionFilters` | Inspect filters |

### Lambda execution role

The managed policy `AWSLambdaBasicExecutionRole` grants:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ],
    "Resource": "*"
  }]
}
```

If this managed policy is detached, Lambda logs silently fail. The
function runs, returns its response, but no log group is created and
no events are ingested. There is no error in the function response —
the Lambda service principal's attempt to create the log group is
denied silently.

### VPC Flow Logs delivery role

The `DeliverLogsPermissionArn` role on a flow log needs:

| Action | Resource |
|---|---|
| `logs:CreateLogGroup` | `arn:aws:logs:<region>:<account>:log-group:<group>` |
| `logs:CreateLogStream` | same group |
| `logs:PutLogEvents` | same group |
| `logs:DescribeLogGroups` / `logs:DescribeLogStreams` | same group |

The managed policy `CloudWatchLogsDeliveryRole` (AWS-managed) or
`AmazonEC2FullAccess` (broader) typically covers this.

### CloudWatch agent IAM

The agent's EC2 IAM role needs the managed policy
`CloudWatchAgentServerPolicy` (or `CloudWatchAgentAdminPolicy` for
configuration management). Without it, the agent starts but cannot
write logs or metrics.

## Lambda log group auto-creation

| Step | Effect |
|---|---|
| First invocation of a new function | The Lambda service principal attempts to create `/aws/lambda/<function-name>` |
| Role has `logs:CreateLogGroup` | Log group is created; first log stream is created; events are ingested |
| Role LACKS `logs:CreateLogGroup` | Creation silently fails; no error in the function response; subsequent invocations continue to drop logs |
| Role has `logs:CreateLogGroup` but LACKS `logs:CreateLogStream` | Log group is created but no stream appears; events are dropped |
| Role has all three but LACKS `logs:PutLogEvents` | Log group and stream are created but events are not ingested |

The diagnosis order: `describe-log-groups` (does the group exist?) →
`describe-log-streams` (any streams?) → `get-log-events` (any events
in the latest stream?) → `simulate-principal-policy` (does the role
have the three required actions?).

## Data protection policy patterns

An account-level or log-group-level data protection policy redacts
sensitive patterns at ingestion time. Common patterns:

| Pattern name | Matches |
|---|---|
| `AWS-API-KEY` | AWS access key IDs (`AKIA...`) |
| `EmailAddress` | RFC 5322 email addresses |
| `CreditCardNumber` | Primary Account Number (credit card) |
| `IPAddress` | IPv4 and IPv6 addresses |
| `PLUDE-USA-SSN` | US Social Security Numbers |
| `PLUDE-USA-PASSPORT` | US passport numbers |

Redacted content appears as `{{REDACTED}}` in `get-log-events` and
Insights query results. The original content is not recoverable after
ingestion. To inspect the policy:

```bash
aws logs get-data-protection-policy --log-group-name <group> --output json
```

Disabling a data protection policy is a security-owner decision; do
not disable without explicit sign-off.

## CloudTrail events for CloudWatch Logs diagnosis

| EventName | Meaning |
|---|---|
| `CreateLogGroup` | A log group was created (by the service principal or a user) |
| `CreateLogStream` | A log stream was created |
| `PutLogEvents` | A batch of events was ingested |
| `DeleteLogGroup` / `DeleteLogStream` | Manual deletion |
| `PutRetentionPolicy` | Retention was changed |
| `PutSubscriptionFilter` / `DeleteSubscriptionFilter` | Subscription filter changed |
| `PutMetricFilter` / `DeleteMetricFilter` | Metric filter changed |
| `PutDataProtectionPolicy` | Data protection policy applied |
| `PutResourcePolicy` | Resource-based policy changed (cross-account) |
| `AssociateKmsKey` | CMK encryption applied to the log group |

Note: retention-driven stream expirations do NOT produce a CloudTrail
event (the deletion is internal to CloudWatch Logs). Operators who
"lost logs but see no DeleteLogStream event" almost always had
retention expiry, not a malicious deletion.
