# Fan-Out, FIFO, and Cross-Region Quick Reference

A focused quick-reference for the SNS-to-SQS fan-out pattern, FIFO
topic/queue ordering semantics, and cross-region delivery permission
surface. Loaded when the diagnostic needs to verify fan-out
durability, FIFO ordering, or cross-region policy grants.

## SNS-to-SQS fan-out pattern

```
                    [SNS topic]
                         │
           ┌─────────────┼─────────────┐
           ▼             ▼             ▼
     [SQS queue A] [SQS queue B] [SQS queue C]
      (orders)     (audit)       (analytics)
           │             │             │
      [consumer A] [consumer B] [consumer C]
```

Each queue has its own subscription and receives every message
independently. A slow or failing consumer on queue B does NOT affect
consumers on queue A or C. This is the durability advantage over
direct SNS-to-Lambda (where a slow Lambda backs up delivery for all
subscriptions on the topic).

### Fan-out subscription requirements

Each SQS subscription needs:
1. A queue policy granting `sqs:SendMessage` to `sns.amazonaws.com`
   scoped to the source topic ARN.
2. `ConfirmationStatus: Confirmed` (auto for console; manual check
   for IaC).
3. Optionally a `FilterPolicy` to scope which messages land in this
   queue.

### Queue policy template

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "sns.amazonaws.com"},
    "Action": "sqs:SendMessage",
    "Resource": "<queue-arn>",
    "Condition": {
      "ArnEquals": {"aws:SourceArn": "<topic-arn>"}
    }
  }]
}
```

### RawMessageDelivery decision

| Need | Setting | Trade-off |
|---|---|---|
| Consumer needs SNS metadata (MessageId, TopicArn, Timestamp) | `false` (default) | 1-4 KB envelope overhead per message |
| Consumer wants just the body; minimal overhead | `true` | Message attributes NOT set on SQS message; consumer must parse from body if needed |
| Large payloads near 256 KB cap | `true` | Removes envelope overhead; prevents SQS cap exceed |

## FIFO topic and queue ordering

### FIFO requirements checklist

| Component | Requirement |
|---|---|
| SNS topic | Name ends in `.fifo`; `FifoTopic: true` |
| SQS queue | Name ends in `.fifo`; `FifoQueue: true` |
| Publisher | Sets `MessageGroupId` for ordering; `MessageDeduplicationId` for exactly-once |
| Subscription | Queue must be `.fifo` (standard queue breaks ordering even on a FIFO topic) |

### MessageGroupId semantics

All messages with the SAME `MessageGroupId` are delivered to a
single consumer in order. Messages with DIFFERENT `MessageGroupId`s
are delivered in parallel (no ordering guarantee across groups).

Common gotcha: if the publisher uses a constant `MessageGroupId` for
all messages, throughput drops to a single consumer stream. If the
publisher uses a unique `MessageGroupId` per message, ordering is
lost (each message is its own group).

### Deduplication

| Dedup method | How | Scope |
|---|---|---|
| `MessageDeduplicationId` | Publisher sets explicitly | Per-queue, 5-minute window |
| Content-based | SNS hashes the body | Per-queue, 5-minute window (topic must have `ContentBasedDeduplication: true`) |

Duplicate deliveries within the 5-minute window are silently
dropped. If the consumer sees duplicates, the publisher is either
sending different `MessageDeduplicationId`s for the same content or
the dedup window has expired.

## Cross-region and cross-account delivery

### Cross-region Lambda subscription

SNS is regional. A topic in `us-east-1` subscribing to a Lambda in
`us-west-2` works, but the Lambda function's resource-based policy
must grant `lambda:InvokeFunction` to `sns.amazonaws.com` with the
source ARN scoped to the topic:

```bash
aws lambda add-permission \
  --function-name <fn> \
  --statement-id AllowCrossRegionSNS \
  --action lambda:InvokeFunction \
  --principal sns.amazonaws.com \
  --source-arn arn:aws:sns:us-east-1:<topic-account>:<topic-name> \
  --region <lambda-region> \
  --profile <p>
```

Console auto-adds for same-region; CLI / Terraform do NOT.

### Cross-account SQS subscription

A topic in account A subscribing to an SQS queue in account B
requires:
1. The queue policy in account B grants `sqs:SendMessage` to
   `sns.amazonaws.com` scoped to the topic ARN in account A.
2. The topic policy in account A allows the publisher to
   `sns:Publish`.

### Cross-account Lambda subscription

Same as cross-region: the function resource policy must grant
`lambda:InvokeFunction` to `sns.amazonaws.com` with `--source-arn`
scoped to the topic in the other account.

## SNS subscription DLQ (RedrivePolicy)

SNS subscriptions support a `RedrivePolicy` attribute (2024-2025)
that routes messages to an SQS DLQ after delivery retry exhaustion.

```json
{
  "deadLetterQueueArn": "arn:aws:sqs:us-east-1:111111111111:sns-dlq"
}
```

This is distinct from a Lambda OnFailure destination:
- SNS subscription DLQ catches messages that SNS itself failed to
  deliver to ANY subscription target (HTTP timeout, Lambda
  invocation failure after retries).
- Lambda OnFailure destination catches messages that Lambda
  processed but the handler returned an error on.

For Lambda subscriptions, configure BOTH: the SNS subscription DLQ
for SNS-side delivery failures, and the Lambda OnFailure destination
for handler-side failures.

## Delivery status logging

Enable delivery status logging on the topic to capture HTTP, Lambda,
and SQS delivery results in CloudWatch Logs:

```bash
aws sns set-topic-attributes \
  --topic-arn <topic-arn> \
  --attribute-name HTTPSuccessFeedbackRoleArn \
  --attribute-value <iam-role-arn> --profile <p>
aws sns set-topic-attributes \
  --topic-arn <topic-arn> \
  --attribute-name HTTPFailureFeedbackRoleArn \
  --attribute-value <iam-role-arn> --profile <p>
```

Repeat for `LambdaSuccessFeedbackRoleArn`,
`LambdaFailureFeedbackRoleArn`, `SQSSuccessFeedbackRoleArn`,
`SQSFailureFeedbackRoleArn` as needed per protocol.

The logs provide per-delivery-attempt detail (HTTP response code,
Lambda error message, SQS error) that CloudWatch metrics aggregate
away. Essential for diagnosing intermittent HTTP 4xx/5xx or Lambda
handler failures.
