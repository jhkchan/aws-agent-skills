# Deployment CLI Commands — SNS Topic Deployer

Full copy-pasteable CLI command sequence for all 10 deployment steps.
Variables to substitute: `<name>`, `<region>`, `<account-id>`,
`<topic-type>`, `<kms-key-id>`, `<bucket-arn>`, `<queue-arn>`.

## Step 0: Prerequisites check

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)
```

## Step 1: Create the topic

```bash
# Standard topic
aws sns create-topic --name order-events

# FIFO topic (name MUST end in .fifo)
aws sns create-topic --name order-events.fifo \
  --attributes FifoTopic=true,ContentBasedDeduplication=true
```

## Step 2: Enable encryption (SSE-KMS)

```bash
# AWS-managed key (same-account subscribers only)
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name KmsMasterKeyId \
  --attribute-value alias/aws/sns

# Customer-managed key (cross-account subscribers)
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name KmsMasterKeyId \
  --attribute-value alias/my-sns-key
```

## Step 3: Set the access policy (if cross-service or cross-account)

### S3 Event Notification pattern

```bash
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name Policy \
  --attribute-value '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": "*",
      "Action": "sns:Publish",
      "Resource": "arn:aws:sns:us-east-1:111111111111:order-events",
      "Condition": {
        "ArnEquals": { "aws:SourceArn": "arn:aws:s3:::order-uploads" }
      }
    }]
  }'
```

### Cross-account publisher

```bash
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name Policy \
  --attribute-value '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::222222222222:root" },
      "Action": "sns:Publish",
      "Resource": "arn:aws:sns:us-east-1:111111111111:order-events"
    }]
  }'
```

### CloudWatch Alarm pattern

```bash
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:alerts \
  --attribute-name Policy \
  --attribute-value '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": { "Service": "cloudwatch.amazonaws.com" },
      "Action": "sns:Publish",
      "Resource": "arn:aws:sns:us-east-1:111111111111:alerts"
    }]
  }'
```

## Step 4: Create subscriptions

### SQS subscription

```bash
# The SQS queue policy must grant SNS sqs:SendMessage
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:111111111111:order-queue \
  --return-subscription-arn
```

### Lambda subscription

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:us-east-1:111111111111:function:order-handler \
  --return-subscription-arn
```

### HTTPS subscription

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --protocol https \
  --notification-endpoint https://api.example.com/sns-webhook \
  --return-subscription-arn
# Note: HTTP/HTTPS subscriptions require manual confirmation
```

### Email subscription

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --protocol email \
  --notification-endpoint ops@example.com
# Note: confirmation email is sent to the address
```

### Firehose subscription

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --protocol firehose \
  --notification-endpoint arn:aws:firehose:us-east-1:111111111111:deliverystream/order-archive \
  --return-subscription-arn
```

## Step 5: Set filter policies

### MessageAttributes filter

```bash
SUB_ARN=$(aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --query 'Subscriptions[?Endpoint==`arn:aws:sqs:us-east-1:111111111111:order-queue`].SubscriptionArn' \
  --output text)

aws sns set-subscription-attributes \
  --subscription-arn "$SUB_ARN" \
  --attribute-name FilterPolicy \
  --attribute-value '{"event_type": ["order_created", "order_shipped"]}'
```

### MessageBody filter

```bash
aws sns set-subscription-attributes \
  --subscription-arn "$SUB_ARN" \
  --attribute-name FilterPolicy \
  --attribute-value '{"event_type": ["order_created"]}'

aws sns set-subscription-attributes \
  --subscription-arn "$SUB_ARN" \
  --attribute-name FilterPolicyScope \
  --attribute-value MessageBody
```

## Step 6: Enable delivery status logging

### Create the IAM role for SNS delivery feedback

```bash
aws iam create-role \
  --role-name SNSDeliveryFeedback \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "sns.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam put-role-policy \
  --role-name SNSDeliveryFeedback \
  --policy-name SNSDeliveryLogs \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:PutMetricFilter",
        "logs:PutRetentionPolicy"
      ],
      "Resource": "*"
    }]
  }'
```

### Enable SQS delivery logging

```bash
FEEDBACK_ROLE=arn:aws:iam::111111111111:role/SNSDeliveryFeedback

aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name SQSSuccessFeedbackRoleArn \
  --attribute-value "$FEEDBACK_ROLE"

aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name SQSFailureFeedbackRoleArn \
  --attribute-value "$FEEDBACK_ROLE"
```

### Enable HTTP/S delivery logging

```bash
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name HTTPSuccessFeedbackRoleArn \
  --attribute-value "$FEEDBACK_ROLE"

aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name HTTPFailureFeedbackRoleArn \
  --attribute-value "$FEEDBACK_ROLE"

# Set sample rate for success logs (0-100, default 0 = no success logs)
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name HTTPSuccessFeedbackSampleRate \
  --attribute-value "100"
```

### Enable Lambda/Application delivery logging

```bash
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name ApplicationSuccessFeedbackRoleArn \
  --attribute-value "$FEEDBACK_ROLE"

aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --attribute-name ApplicationFailureFeedbackRoleArn \
  --attribute-value "$FEEDBACK_ROLE"
```

## Step 7: Set subscription-level DLQ

```bash
# Create the DLQ (SQS queue)
aws sqs create-queue \
  --queue-name sns-order-events-dlq \
  --attributes MessageRetentionPeriod=1209600,SqsManagedSseEnabled=true

DLQ_ARN=$(aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/sns-order-events-dlq \
  --attribute-names QueueArn \
  --query 'Attributes.QueueArn' --output text)

# Grant SNS permission to write to the DLQ
aws sqs set-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/sns-order-events-dlq \
  --attributes Policy='{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "sns.amazonaws.com"},
      "Action": "sqs:SendMessage",
      "Resource": "arn:aws:sqs:us-east-1:111111111111:sns-order-events-dlq"
    }]
  }'

# Attach DLQ to the subscription
aws sns set-subscription-attributes \
  --subscription-arn "$SUB_ARN" \
  --attribute-name RedrivePolicy \
  --attribute-value "{\"deadLetterTargetArn\":\"$DLQ_ARN\"}"
```

## Step 8: Mobile push setup

### Create platform application

```bash
# APNS (Apple)
aws sns create-platform-application \
  --name MyAppAPNS \
  --platform APNS \
  --attributes PlatformCredential=<private-key>,PlatformPrincipal=<certificate>

# FCM (Android)
aws sns create-platform-application \
  --name MyAppFCM \
  --platform FCM \
  --attributes PlatformCredential=<server-key>
```

### Register device endpoint

```bash
aws sns create-platform-endpoint \
  --platform-application-arn arn:aws:sns:us-east-1:111111111111:app/APNS/MyAppAPNS \
  --token <device-token> \
  --custom-user-data '{"userId": "12345"}'
```

### Publish to mobile endpoint

```bash
aws sns publish \
  --target-arn arn:aws:sns:us-east-1:111111111111:endpoint/APNS/MyAppAPNS/xxxxx \
  --message-structure json \
  --message '{
    "default": "{\"message\":\"Order shipped\"}",
    "APNS": "{\"aps\":{\"alert\":\"Order shipped\"},\"orderId\":\"12345\"}",
    "FCM": "{\"notification\":{\"title\":\"Order shipped\",\"body\":\"Order #12345\"},\"data\":{\"orderId\":\"12345\"}}"
  }'
```

## Step 9: S3 Event Notification to SNS

```bash
aws s3api put-bucket-notification-configuration \
  --bucket order-uploads \
  --notification-configuration '{
    "TopicConfigurations": [{
      "TopicArn": "arn:aws:sns:us-east-1:111111111111:order-events",
      "Events": ["s3:ObjectCreated:*"]
    }]
  }'
```

## Step 10: Verification

```bash
TOPIC_ARN=arn:aws:sns:us-east-1:111111111111:order-events

# Topic attributes (all configuration)
aws sns get-topic-attributes --topic-arn "$TOPIC_ARN" --output json

# List subscriptions
aws sns list-subscriptions-by-topic --topic-arn "$TOPIC_ARN"

# Verify encryption
aws sns get-topic-attributes --topic-arn "$TOPIC_ARN" \
  --query 'Attributes.KmsMasterKeyId' --output text

# Verify delivery logging
aws sns get-topic-attributes --topic-arn "$TOPIC_ARN" \
  --query 'Attributes.SQSFailureFeedbackRoleArn' --output text

# Test publish (standard topic)
aws sns publish \
  --topic-arn "$TOPIC_ARN" \
  --message '{"test": true}'

# Test publish (FIFO topic — requires MessageGroupId)
aws sns publish \
  --topic-arn "$FIFO_TOPIC_ARN" \
  --message '{"test": true}' \
  --message-group-id "test-group"
```
