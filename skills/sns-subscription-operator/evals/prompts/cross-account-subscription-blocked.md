# Eval prompt: cross-account-subscription-blocked

Plan the following cross-account SNS subscription creation and emit the
standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, NOTES).

Operation: create
TopicArn: arn:aws:sns:us-east-1:222222222222:shared-events
Protocol: sqs
Endpoint: arn:aws:sqs:us-east-1:111111111111:my-queue

```json
{
  "TopicAttributes": {
    "Owner": "222222222222",
    "Policy": {
      "allowsSubscribeFor": ["arn:aws:iam::222222222222:root"],
      "doesNotInclude": "111111111111"
    }
  },
  "QueueAttributes": {
    "QueueArn": "arn:aws:sqs:us-east-1:111111111111:my-queue",
    "PolicyAllowsSnsSendMessage": false
  },
  "CallingIdentity": "arn:aws:iam::111111111111:role/AppDeployRole"
}
```
