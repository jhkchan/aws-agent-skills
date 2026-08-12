# Example usage: sqs-dead-letter-troubleshooter

A walkthrough showing the skill diagnosing a FIFO queue stall caused by
a poison message in a specific MessageGroupId, demonstrating the
group-level blocking effect, the evidence-backed ROOT_CAUSE_IDENTIFIED
verdict, and the targeted remediation.

## Input (user prompt)

> Our FIFO queue `orders.fifo` throughput dropped to near-zero for
> customer "cust-9912" at 14:30 UTC. Other customers are fine. The DLQ
> `orders-dlq.fifo` has 23 messages, all from the same customer group.
> Help us find the root cause.

```text
SourceQueueURL: https://sqs.us-east-1.amazonaws.com/111111111111/orders.fifo
DLQArn: arn:aws:sqs:us-east-1:111111111111:orders-dlq.fifo
RedrivePolicy:
  deadLetterTargetArn: "arn:aws:sqs:us-east-1:111111111111:orders-dlq.fifo"
  maxReceiveCount: "5"
VisibilityTimeout: 120
MessageRetentionPeriod: 1209600
FifoQueue: true

Consumer: Lambda fn-sqs-fifo-consumer
Lambda Timeout: 60
Lambda EventSourceMapping:
  BatchSize: 10
  VisibilityTimeout: 120

DLQ message inspection (10 samples):
  All have Attributes.MessageGroupId = "cust-9912"
  First message (by SentTimestamp):
    ApproximateReceiveCount: 5
    Body: "{bad json: missing closing brace"
  Remaining 9 messages also MessageGroupId "cust-9912"

Lambda logs:
  Repeated "SyntaxError: Unexpected token" for MessageGroupId
    "cust-9912" starting at 14:30 UTC
  No errors for other MessageGroupIds

CloudWatch metrics (last hour):
  - Lambda Throttles: 0
  - Lambda Duration p99: 8s (well within VT of 120s)
  - Source queue ApproximateNumberOfMessages: stable for non-cust-9912
```

## Skill output

```text
TARGET: orders.fifo → orders-dlq.fifo
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: FIFO queue orders.fifo has a poison message in MessageGroupId
  "cust-9912" that has been received 5 times (maxReceiveCount=5) without
  successful processing. The message contains a malformed JSON payload
  that causes the consumer Lambda to throw a JSON parse error. All
  messages behind it in MessageGroupId "cust-9912" are blocked by FIFO
  ordering guarantees. Other MessageGroupIds are flowing normally
  (Step 5).
LAYER: FIFO_POISON_MESSAGE
EVIDENCE:
  - Symptom: FIFO queue orders.fifo throughput dropped to near-zero for
    customer cust-9912 at 14:30 UTC. Other customer groups continue
    processing normally. DLQ orders-dlq.fifo has accumulated 23 messages
    in the last hour, all with MessageGroupId "cust-9912".
  - Probe: aws sqs receive-message on orders-dlq.fifo returns 10
    messages, ALL with Attributes.MessageGroupId = "cust-9912". The
    first message (by SentTimestamp) has ApproximateReceiveCount: 5 and
    Body containing "{bad json: missing closing brace".
  - Probe: aws logs filter-log-events on the consumer Lambda shows
    repeated "SyntaxError: Unexpected token" for MessageGroupId
    "cust-9912" starting at 14:30 UTC.
  - Passing: maxReceiveCount is 5 (reasonable); VisibilityTimeout is
    120s (exceeds Lambda Duration p99 of 8s); Lambda Throttles = 0;
    other MessageGroupIds are processing normally (no concurrency issue).
REMEDIATION:
  1. The poison message is already in the DLQ (receive count reached
     maxReceiveCount). The next message in MessageGroupId "cust-9912"
     should now be deliverable. Verify:
     aws sqs get-queue-attributes --queue-url <orders.fifo-url> \
       --attribute-names ApproximateNumberOfMessages --output json
  2. Fix the consumer to handle malformed JSON gracefully:
     try { JSON.parse(record.body) } catch { return batchItemFailures
     with only the bad record's messageId }
  3. Delete the poison message from the DLQ:
     aws sqs delete-message --queue-url <orders-dlq.fifo-url> \
       --receipt-handle <handle>
  4. Implement ReportBatchItemFailures in the Lambda to prevent one bad
     record from poisoning the entire batch.
CONFIRM: Before deleting the poison message and updating the Lambda,
  emit and await: "CONFIRM: About to delete the malformed message from
  orders-dlq.fifo and redeploy fn-sqs-fifo-consumer with JSON error
  handling. Proceed? (yes/no)"
  Do NOT run the CLI until the operator replies yes.
```

## What the skill caught that a generic assistant misses

1. **Recognized the FIFO group-level blocking effect.** A generic
   assistant sees "FIFO queue stuck" and diagnoses a queue-wide problem.
   The skill recognizes that only MessageGroupId "cust-9912" is affected
   while other groups flow normally — the problem is one specific message
   in one specific group.

2. **Inspected DLQ message bodies for the failure pattern.** The skill
   reads the actual DLQ message body and finds the malformed JSON
   `"{bad json: missing closing brace"`. The consumer Lambda throws a
   SyntaxError on every attempt to parse it — a deterministic failure
   that retries cannot fix.

3. **Correlated Lambda logs with the MessageGroupId.** The skill cross-
   references Lambda logs showing "SyntaxError: Unexpected token" for
   only the "cust-9912" group, confirming the consumer code fails on
   this specific payload shape.

4. **Ruled out concurrency, visibility timeout, and maxReceiveCount with
   positive evidence.** Lambda Throttles = 0, Duration p99 of 8s is
   well within the 120s VT, and maxReceiveCount of 5 is reasonable. These
   layers are eliminated with evidence, not assumption.

5. **Explained the FIFO unblocking sequence.** The skill clarifies that
   once the poison message moves to the DLQ, the next message in
   MessageGroupId "cust-9912" becomes deliverable — the group is
   unblocked. But the consumer must be fixed to handle bad JSON, or the
   next message with the same shape will also fail.

## Slash-command invocation

```
/aws:troubleshoot-sqs-dead-letter
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why orders.fifo DLQ is filling"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: sqs-dead-letter-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After fixing the consumer and clearing the poison message, verify the
FIFO queue recovers:

```bash
# Confirm the poison message is deleted from the DLQ
aws sqs get-queue-attributes \
  --queue-url <orders-dlq.fifo-url> \
  --attribute-names ApproximateNumberOfMessages \
  --profile default --output json

# Confirm the source queue is draining for cust-9912
aws cloudwatch get-metric-statistics --namespace AWS/SQS \
  --metric-name ApproximateNumberOfMessagesVisible \
  --dimensions Name=QueueName,Value=orders.fifo \
  --start-time $(date -d '-30 minutes' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average \
  --profile default --output json

# Confirm the Lambda is processing without SyntaxErrors
aws logs filter-log-events \
  --log-group-name /aws/lambda/fn-sqs-fifo-consumer \
  --start-time $(date -d '-15 minutes' +%s)000 \
  --filter-pattern '"SyntaxError"' \
  --profile default --output json
```

Then monitor the DLQ message count for 30-60 minutes to confirm no new
messages arrive from MessageGroupId "cust-9912".
