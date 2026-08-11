# Eval prompt: delivery-policy-dlq-setup

Plan the following SNS subscription delivery policy + DLQ configuration
and emit the standard VERDICT block (OPERATION, VERDICT, TARGET,
PRE_CHECKS, STEPS, POST_VERIFY, NOTES).

Operation: set-delivery-policy
TopicArn: arn:aws:sns:us-east-1:111111111111:alert-notifications
SubscriptionArn: arn:aws:sns:us-east-1:111111111111:alert-notifications:5678-efgh
Protocol: https
Endpoint: https://api.example.com/webhook

```json
{
  "DesiredDeliveryPolicy": {
    "numRetries": 5,
    "minDelayTarget": 1,
    "maxDelayTarget": 16,
    "backoffFunction": "exponential"
  },
  "DesiredDLQ": "arn:aws:sqs:us-east-1:111111111111:sns-dlq",
  "DLQCheck": {
    "QueueArn": "arn:aws:sqs:us-east-1:111111111111:sns-dlq",
    "PolicyAllowsSnsSendMessage": true,
    "ConditionArnEquals": "arn:aws:sns:us-east-1:111111111111:alert-notifications"
  },
  "SubscriptionAttributes": {
    "PendingConfirmation": false
  }
}
```
