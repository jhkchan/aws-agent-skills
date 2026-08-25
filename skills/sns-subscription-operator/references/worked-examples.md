# Worked Examples — SNS Subscription Operator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Worked example — diagnose subscription not receiving messages

```text
OPERATION: diagnose
VERDICT: COMPLETED
TARGET: arn:aws:sns:us-east-1:111111111111:order-events (subscription:
        arn:aws:sns:us-east-1:111111111111:order-events:1234-abcd,
        protocol: sqs, endpoint:
        arn:aws:sqs:us-east-1:111111111111:order-processing-queue,
        account 111111111111, region us-east-1)
PRE_CHECKS:
  - [PASS] Subscription exists, PendingConfirmation: false (confirmed)
  - [PASS] Queue policy allows sqs:SendMessage from topic ARN
  - [FAIL] Filter policy does not match publisher's message attributes
    — filter requires {"event_type": ["order_created"]} but publisher
    sends message attribute "type" (not "event_type"). All messages are
    silently dropped by the filter.
STEPS:
  1. Fix the filter policy to match the publisher's attribute name:
     aws sns set-subscription-attributes \
       --subscription-arn arn:aws:sns:us-east-1:111111111111:order-events:1234-abcd \
       --attribute-name FilterPolicy \
       --attribute-value '{"type": ["order_created", "order_updated"]}'
  2. Publish a test message with message attribute type=order_created:
     aws sns publish \
       --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
       --message '{"order_id": "test-123"}' \
       --message-attributes '{"type": {"DataType": "String", "StringValue": "order_created"}}'
  3. Verify the message is received by the SQS queue:
     aws sqs receive-message --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/order-processing-queue
POST_VERIFY:
  - [PASS] Filter policy updated to match publisher attributes
  - [PASS] Test message with type=order_created received by queue
  - [PASS] CloudTrail shows SetSubscriptionAttributes event
NOTES:
  - Root cause: attribute name mismatch. The filter policy used
    "event_type" but the publisher sends "type". This is the #1 cause
    of SNS filter-policy non-delivery.
  - Recommendation: standardize on a single attribute naming convention
    across all publishers. Consider using SNS message data protection
    to audit attribute names at the topic level.
```

### Worked example — set delivery policy with DLQ

```text
OPERATION: set-delivery-policy
VERDICT: READY
TARGET: arn:aws:sns:us-east-1:111111111111:order-events (subscription:
        arn:aws:sns:us-east-1:111111111111:order-events:5678-efgh,
        protocol: https, endpoint: https://api.example.com/webhook,
        account 111111111111, region us-east-1)
PRE_CHECKS:
  - [PASS] Subscription exists, PendingConfirmation: false
  - [PASS] Delivery policy JSON valid (5 retries, exponential backoff)
  - [PASS] DLQ SQS ARN exists (arn:aws:sqs:us-east-1:111111111111:sns-dlq)
  - [PASS] DLQ queue policy allows sqs:SendMessage from SNS service
  - [PASS] DLQ is not the same as the subscription endpoint (no loop)
STEPS:
  1. CONFIRM: About to set delivery policy and DLQ on subscription
     5678-efgh. Retry: 5 attempts, exponential backoff (1s-16s).
     DLQ: arn:aws:sqs:us-east-1:111111111111:sns-dlq. Proceed? (yes/no)
  2. aws sns set-subscription-attributes \
       --subscription-arn arn:aws:sns:us-east-1:111111111111:order-events:5678-efgh \
       --attribute-name DeliveryPolicy \
       --attribute-value '{"healthyRetryPolicy": {"numRetries": 5, "minDelayTarget": 1, "maxDelayTarget": 16, "numMinDelayRetries": 2, "numMaxDelayRetries": 3, "backoffFunction": "exponential"}}'
  3. aws sns set-subscription-attributes \
       --subscription-arn arn:aws:sns:us-east-1:111111111111:order-events:5678-efgh \
       --attribute-name RedrivePolicy \
       --attribute-value '{"deadLetterTargetArn": "arn:aws:sqs:us-east-1:111111111111:sns-dlq"}'
  4. Verify: aws sns get-subscription-attributes \
       --subscription-arn arn:aws:sns:us-east-1:111111111111:order-events:5678-efgh
POST_VERIFY: (pending execution)
NOTES:
  - Retry: 5 attempts, exponential backoff (1s, 2s, 4s, 8s, 16s).
    Total window: ~31 seconds. DLQ: messages failing all 5 retries go
    to sns-dlq. Monitor via CloudWatch Alarm on
    ApproximateNumberOfMessagesVisible. Replay from DLQ after fixing
    the endpoint.
```

### Worked example — cross-account subscription BLOCKED

```text
OPERATION: create
VERDICT: BLOCKED
TARGET: arn:aws:sns:us-east-1:222222222222:shared-events (subscription:
        new, protocol: sqs, endpoint:
        arn:aws:sqs:us-east-1:111111111111:my-queue,
        subscriber 111111111111, topic owner 222222222222, us-east-1)
PRE_CHECKS:
  - [PASS] Topic exists in account 222222222222
  - [PASS] Protocol sqs valid, endpoint SQS ARN valid
  - [FAIL] Topic policy does not allow sns:Subscribe for account
    111111111111 (only allows topic owner 222222222222).
  - [FAIL] Queue policy in account 111111111111 does not allow
    sqs:SendMessage from the topic ARN in account 222222222222.
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
NOTES:
  - Root cause: cross-account subscription requires BOTH sides'
    permission. Fix on topic owner side (222222222222): add
    sns:Subscribe for arn:aws:iam::111111111111:root to the topic
    policy. Fix on queue owner side (111111111111): add
    sqs:SendMessage from sns.amazonaws.com with Condition
    ArnEquals aws:SourceArn = the topic ARN to the queue policy.
```
