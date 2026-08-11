# Eval prompt: http-subscription-pending-confirmation

Plan the following SNS subscription confirmation and emit the standard
VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, NOTES).

Operation: confirm
TopicArn: arn:aws:sns:us-east-1:111111111111:alert-notifications
SubscriptionArn: arn:aws:sns:us-east-1:111111111111:alert-notifications:9f8e7d6c-1234
Protocol: https
Endpoint: https://hooks.example.com/sns

```json
{
  "SubscriptionAttributes": {
    "PendingConfirmation": true,
    "ConfirmationWasAuthenticated": false
  },
  "EndpointCheck": {
    "method": "HEAD",
    "url": "https://hooks.example.com/sns",
    "status": 200
  },
  "Token": "51b2ff37-extended-token-xyz"
}
```
