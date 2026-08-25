# Diagnostic Commands — SNS Subscription Operator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Live-account pre-flight

**Live-account pre-flight (skip if offline plan audit):**
1. `aws sns get-topic-attributes --topic-arn <arn>` — confirm topic
   exists, capture the topic policy (`Policy` attribute), and the
   topic owner account.
2. `aws sns list-subscriptions-by-topic --topic-arn <arn>` — capture
   existing subscriptions, their `SubscriptionArn`, `Protocol`,
   `Endpoint`, and `PendingConfirmation` status.
3. For SQS endpoints: `aws sqs get-queue-attributes --queue-url <url>
   --attribute-names Policy` — verify the queue policy allows
   `sqs:SendMessage` from the SNS topic ARN.
4. For Lambda endpoints: `aws lambda get-policy --function-name <name>`
   — verify the Lambda resource policy allows
   `lambda:InvokeFunction` from the SNS topic ARN.
5. For Firehose endpoints: `aws firehose describe-delivery-stream
   --delivery-stream-name <name>` — verify the stream is `ACTIVE`.
6. For HTTP/HTTPS endpoints: verify the endpoint is reachable and
   returns a 2xx for a HEAD request. SNS requires the endpoint to
   return 200 for the confirmation POST.
7. For filter policies: validate the JSON is well-formed and within
   the 30 KB size limit.
8. For DLQ (redrive): verify the DLQ SQS ARN exists and the queue
   policy allows `sqs:SendMessage` from the SNS topic ARN.
