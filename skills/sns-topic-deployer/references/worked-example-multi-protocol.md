# Worked Example: Multi-Protocol Topic — SNS Topic Deployer

A realistic topic (`order-events`) with four subscription protocols —
HTTPS webhook, SQS queue, Lambda function, and mobile push (APNS) —
covering the per-protocol configuration each needs. Standard topic in
us-east-1 with SSE-KMS using a customer-managed CMK (Lambda lives in a
different account).

## Step-by-step configuration

```bash
# === Step 1: Create the topic (Standard — we have HTTP + Lambda + mobile) ===
aws sns create-topic --name order-events
# Returns: arn:aws:sns:us-east-1:111111111111:order-events

# === Step 2: Enable SSE-KMS with a customer-managed CMK (cross-account Lambda) ===
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name KmsMasterKeyId \
  --attribute-value alias/my-sns-key
# The CMK key policy MUST grant account 222222222222 (Lambda owner):
#   kms:Decrypt + kms:GenerateDataKey* with kms:ViaService = sns.us-east-1.amazonaws.com

# === Step 3: Subscribe HTTPS webhook (intra-account) ===
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --protocol https \
  --notification-endpoint https://api.example.com/sns/order-webhook \
  --return-subscription-arn
# PendingConfirmation. Endpoint MUST handle SubscriptionConfirmation POST.

# Programmatic confirmation (server-side):
TOKEN=$(curl -s https://api.example.com/sns/latest-token)
aws sns confirm-subscription \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --token $TOKEN \
  --authenticate-on-unsubscribe

# === Step 4: Subscribe SQS queue (intra-account, with KMS) ===
aws sqs set-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/order-queue \
  --attributes '{"Policy": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"sns.amazonaws.com\"},\"Action\":\"sqs:SendMessage\",\"Resource\":\"arn:aws:sqs:us-east-1:111111111111:order-queue\",\"Condition\":{\"ArnEquals\":{\"aws:SourceArn\":\"arn:aws:sns:us-east-1:111111111111:order-events\"}}}]}"}'

aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:111111111111:order-queue \
  --return-subscription-arn
# Same-account SQS auto-confirms.

# === Step 5: Subscribe cross-account Lambda function (account 222222222222) ===
# In the Lambda account (222222222222):
aws lambda add-permission \
  --function-name order-handler \
  --statement-id AllowSNSInvoke \
  --action lambda:InvokeFunction \
  --principal sns.amazonaws.com \
  --source-arn arn:aws:sns:us-east-1:111111111111:order-events

# Back in the topic account (111111111111):
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:us-east-1:222222222222:function:order-handler \
  --return-subscription-arn
# Cross-account Lambda does NOT auto-confirm. Lambda account must confirm:
#   aws sns confirm-subscription --topic-arn <arn> --token <token>

# === Step 6: Configure filter policies ===
SQS_SUB_ARN=$(aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --query 'Subscriptions[?Endpoint==`arn:aws:sqs:us-east-1:111111111111:order-queue`].SubscriptionArn' \
  --output text)

aws sns set-subscription-attributes \
  --subscription-arn $SQS_SUB_ARN \
  --attribute-name FilterPolicy \
  --attribute-value '{"event_type": ["order_created"], "region": [{"prefix": "us-"}]}'

LAMBDA_SUB_ARN=$(aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --query 'Subscriptions[?Endpoint==`arn:aws:lambda:us-east-1:222222222222:function:order-handler`].SubscriptionArn' \
  --output text)

aws sns set-subscription-attributes \
  --subscription-arn $LAMBDA_SUB_ARN \
  --attribute-name FilterPolicy \
  --attribute-value '{"event_type": ["order_created", "order_shipped"]}'

# === Step 7: Attach subscription DLQ to the HTTPS subscription ===
HTTPS_SUB_ARN=$(aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --query 'Subscriptions[?Endpoint==`https://api.example.com/sns/order-webhook`].SubscriptionArn' \
  --output text)

aws sns set-subscription-attributes \
  --subscription-arn $HTTPS_SUB_ARN \
  --attribute-name RedrivePolicy \
  --attribute-value '{"deadLetterTargetArn":"arn:aws:sqs:us-east-1:111111111111:order-https-dlq"}'

# === Step 8: Configure mobile push (APNS) subscriber ===
aws sns create-platform-endpoint \
  --platform-application-arn arn:aws:sns:us-east-1:111111111111:app/APNS/MyAppAPNS \
  --token <device-token> \
  --custom-user-data '{"userId": "customer-67890"}'
# Returns: arn:aws:sns:us-east-1:111111111111:endpoint/APNS/MyAppAPNS/abcd1234
# Mobile push is direct-publish alongside the topic (not topic-subscribed).

# === Step 9: Enable delivery status logging (HTTP + Lambda + SQS failure) ===
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name HTTPSuccessFeedbackRoleArn \
  --attribute-value arn:aws:iam::111111111111:role/SNSDeliveryFeedback
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name HTTPFailureFeedbackRoleArn \
  --attribute-value arn:aws:iam::111111111111:role/SNSDeliveryFeedback
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name LambdaFailureFeedbackRoleArn \
  --attribute-value arn:aws:iam::111111111111:role/SNSDeliveryFeedback
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name SQSFailureFeedbackRoleArn \
  --attribute-value arn:aws:iam::111111111111:role/SNSDeliveryFeedback
# IMPORTANT: also add CloudWatch Logs resource policy granting SNS
# logs:CreateLogStream + logs:PutLogEvents.

# === Step 10: Test publish ===
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --subject "Order Created" \
  --message '{"orderId": "ORD-12345", "customerId": "CUST-67890", "total": 99.95}' \
  --message-attributes '{"event_type": {"DataType": "String", "StringValue": "order_created"}, "region": {"DataType": "String", "StringValue": "us-east-1"}}'
```

## Verification

```bash
# Confirm all subscriptions are Confirmed
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --query 'Subscriptions[].{Endpoint:Endpoint,Status:SubscriptionArn}'

# Verify delivery logs
aws logs filter-log-events \
  --log-group-name sns/us-east-1/111111111111/order-events/Failure \
  --log-stream-names $(aws logs describe-log-streams \
    --log-group-name sns/us-east-1/111111111111/order-events/Failure \
    --query 'logStreams[*].logStreamName' --output text)

# Verify the SQS queue received the message
aws sqs receive-message --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/order-queue \
  --max-number-of-messages 10
```

## Per-protocol outcome summary

| Protocol | Filter | DLQ | Delivery logging |
|---|---|---|---|
| HTTPS webhook | `event_type: order_created`, `region: us-*` | order-https-dlq | success + failure |
| SQS queue | `event_type: order_created`, `region: us-*` | (SQS own DLQ) | failure only |
| Lambda (cross-account) | `event_type: [order_created, order_shipped]` | (Lambda on-failure dest) | failure only |
| Mobile push (APNS) | N/A (direct publish) | N/A | failure only |

## Per-protocol retry and dead-letter behavior

| Protocol | Retry policy | Dead-letter target |
|---|---|---|
| HTTP/HTTPS | 4 hours (100,010 attempts), exponential backoff | **Subscription DLQ** (RedrivePolicy) |
| Lambda (async) | Lambda retries 2 times (on top of SNS delivery) | **Lambda on-failure destination** (NOT SNS subscription DLQ) |
| SQS | SNS delivers once; SQS handles downstream | **SQS DLQ** (queue RedrivePolicy, NOT SNS subscription DLQ) |
| Email | One attempt, no retry | None — fire-and-forget |
| Mobile push | Per platform policy (APNS: immediate; FCM: backoff) | **Subscription DLQ** if topic-subscribed |

## Edge-case callouts

- **Cross-account Lambda KMS decrypt:** Lambda in account 222222222222
  must have role policy granting `kms:Decrypt` on the topic CMK. Without
  it, invocation succeeds but function receives opaque ciphertext.
- **Filter policy on HTTPS subscription:** scope at the subscription level
  — topic-level filters do not exist.
- **Mobile push is direct-publish, not topic-subscribed:** to fan out
  topic messages to mobile, use a separate Lambda subscriber that calls
  `publish --target-arn <mobile-endpoint>` for each relevant message.
- **PendingConfirmation on HTTPS:** if webhook does not handle
  `SubscriptionConfirmation` programmatically, subscription stays
  PendingConfirmation for 3 days then expires. Re-subscribing generates
  a new token.
