# Eval prompt: trigger-rotation-reserved-concurrency-zero-blocked

Plan the following Secrets Manager manual rotation trigger and emit the
standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, NOTES).

Operation: trigger-rotation
Secret: prod/orders-service-token
Trigger immediately: yes

```json
{
  "SecretMetadata": {
    "Name": "prod/orders-service-token",
    "RotationEnabled": true,
    "RotationLambdaARN": "arn:aws:lambda:us-east-1:111111111111:function:OrdersServiceTokenRotation",
    "RotationRules": {"AutomaticallyAfterDays": 7},
    "LastRotatedDate": "2026-07-01T03:14:22Z",
    "KmsKeyId": "aws/secretsmanager",
    "VersionIdsToStages": {
      "v1": ["AWSPREVIOUS"],
      "v2": ["AWSCURRENT"]
    },
    "PrimaryRegion": null,
    "DeletedDate": null
  },
  "LambdaMetadata": {
    "FunctionName": "OrdersServiceTokenRotation",
    "State": "Active",
    "Runtime": "python3.12",
    "Timeout": 10,
    "Role": "arn:aws:iam::111111111111:role/service-role/OrdersServiceTokenRotationRole"
  },
  "LambdaConcurrency": {
    "ReservedConcurrentExecutions": 0
  },
  "LambdaCloudWatchMetrics": {
    "Throttles": "14 spikes at 03:00 UTC (the scheduled rotation time) in last 7 days",
    "Errors": 0,
    "Invocations": 0
  }
}
```
