# Eval prompt: lambda-subscription-no-invoke-permission

Diagnose the SNS delivery issue for the following subscription. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: Lambda subscription on topic `order-events` never invokes
the function `fn-order-processor`. The function has zero invocations
in CloudWatch. `NumberOfNotificationsDelivered` is 0 for this
subscription.

```text
TopicArn: arn:aws:sns:us-east-1:111111111111:order-events
SubscriptionArn: arn:aws:sns:us-east-1:111111111111:order-events:def
Protocol: lambda
Endpoint: arn:aws:lambda:us-east-1:111111111111:function:fn-order-processor
ConfirmationStatus: Confirmed
FilterPolicy: (none)

Lambda context:
  - Function fn-order-processor exists, State: Active,
    LastUpdateStatus: Successful.
  - Function resource-based policy (get-policy):
      Statements allow API Gateway invoke and a CI/CD test principal.
      NO statement grants sns.amazonaws.com lambda:InvokeFunction.
  - Subscription was created via Terraform (IaC), not the console.

CloudWatch metrics (last hour):
  - NumberOfNotificationsPublished: 5000 (for the topic)
  - NumberOfNotificationsDelivered: 0 (for this subscription)
  - Lambda Invocations: 0
  - Lambda Errors: 0
```

The function exists and is Active. The subscription is Confirmed with
no filter policy. Identify why SNS never invokes the function.
