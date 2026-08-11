# End-to-end usage scenario: sns-subscription-operator

A walkthrough showing the skill planning an SQS subscription creation
with a filter policy and RawMessageDelivery, all pre-checks passing,
and the operator confirming at the CONFIRM gate. Contrasted with the
diagnose case where a filter-policy attribute mismatch silently blocks
all messages.

## Input (user prompt)

> Create an SQS subscription on `order-events` topic for the
> `order-processing-queue`. Only deliver order_created and order_updated
> events. Use raw message delivery — the Lambda trigger on the queue
> expects the message body directly.

```json
{
  "Operation": "create",
  "TopicArn": "arn:aws:sns:us-east-1:111111111111:order-events",
  "Protocol": "sqs",
  "Endpoint": "arn:aws:sqs:us-east-1:111111111111:order-processing-queue",
  "DesiredFilterPolicy": {"event_type": ["order_created", "order_updated"]},
  "DesiredRawMessageDelivery": true,
  "TopicAttributes": {"Owner": "111111111111", "PolicyAllowsSubscribe": true},
  "QueueAttributes": {"PolicyAllowsSnsSendMessage": true},
  "CallerOwnsTopicAndQueue": true
}
```

## Skill output

```text
OPERATION: create
VERDICT: READY
TARGET: arn:aws:sns:us-east-1:111111111111:order-events (subscription:
        new, protocol: sqs, endpoint:
        arn:aws:sqs:us-east-1:111111111111:order-processing-queue,
        account 111111111111, region us-east-1)
PRE_CHECKS:
  - [PASS] Topic exists (arn:aws:sns:us-east-1:111111111111:order-events)
  - [PASS] Protocol sqs valid
  - [PASS] Endpoint is a valid SQS ARN
  - [PASS] Topic policy allows sns:Subscribe for caller account
  - [PASS] Queue policy allows sqs:SendMessage from topic ARN
  - [PASS] Filter policy JSON valid ({"event_type": ["order_created",
    "order_updated"]}, 48 bytes < 30 KB limit)
  - [PASS] Caller owns the SQS queue (auto-confirmation applies)
STEPS:
  1. CONFIRM: About to create an SNS subscription on topic
     arn:aws:sns:us-east-1:111111111111:order-events, protocol sqs,
     endpoint arn:aws:sqs:us-east-1:111111111111:order-processing-queue.
     Filter policy: {"event_type": ["order_created", "order_updated"]}.
     RawMessageDelivery: true. Auto-confirmation applies (caller owns
     the queue). Proceed? (yes/no)
  2. aws sns subscribe \
       --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
       --protocol sqs \
       --notification-endpoint arn:aws:sqs:us-east-1:111111111111:order-processing-queue \
       --attributes file://attrs.json
  3. Capture the returned SubscriptionArn for verification.
POST_VERIFY: (pending execution)
NOTES:
  - Auto-confirmation applies because the caller owns the SQS queue.
  - Filter policy: only messages with message attribute event_type in
    [order_created, order_updated] will be delivered.
  - RawMessageDelivery: true — the queue receives only the Message body.
```

## What the skill caught that a generic assistant misses

1. **Pre-check gate with 7 checks.** A generic assistant emits the
   subscribe CLI directly. The skill verifies topic existence, protocol
   validity, endpoint format, topic policy permission, queue policy
   permission, filter-policy JSON validity, and auto-confirmation
   eligibility — before executing.

2. **Filter-policy match verification.** A generic assistant applies the
   filter policy without checking whether the publisher's message
   attributes match. The skill surfaces the attribute-name dependency:
   the publisher must include `event_type` as a message attribute, or
   all messages are silently dropped.

3. **RawMessageDelivery context.** A generic assistant mentions it in
   passing. The skill explains WHY it matters: the Lambda trigger on
   the queue receives the message body directly (no SNS envelope
   parsing needed).

4. **Auto-confirmation awareness.** A generic assistant may tell the
   operator to "confirm the subscription" even for SQS subscriptions
   owned by the caller. The skill confirms auto-confirmation applies
   and explains the SubscriptionArn is returned immediately.

5. **CONFIRM gate.** A generic assistant runs the CLI directly. The
   skill emits `CONFIRM:` and waits — a wrong filter policy or
   endpoint can silently break delivery.

6. **Diagnose pattern for filter-policy mismatch.** If the subscription
   was not delivering messages, the skill would identify the attribute
   name mismatch (e.g., publisher sends `type` not `event_type`), fix
   the filter policy, run a test publish, and verify receipt.

## Slash-command invocation

```
/aws:operate-sns-subscription
```

Or via the orchestrator:

```
/aws:pipeline
You: "subscribe my SQS queue to the order-events topic with a filter"
```

The orchestrator emits
`[Phase: Operate | Skills routed: sns-subscription-operator]` and hands
off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "create SNS subscription on order-events"
# [Phase: Operate | Skills routed: sns-subscription-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After creating the subscription, validate the posture:

```bash
# Verify the subscription is confirmed and attributes are correct
aws sns get-subscription-attributes \
  --subscription-arn <sub-arn> --profile default --output json

# Publish a test message with the expected attributes
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --message '{"order_id": "test-001"}' \
  --message-attributes '{"event_type": {"DataType": "String", "StringValue": "order_created"}}' \
  --profile default

# Verify the message arrived in the SQS queue
aws sqs receive-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/order-processing-queue \
  --profile default
```

Then monitor CloudWatch metrics for `NumberOfMessagesPublished` (topic)
and `NumberOfNotificationsDelivered` (subscription) to confirm steady-
state delivery.
