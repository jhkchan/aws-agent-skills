# Eval: custom-cooldown-tuning

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — TargetValue=50, ScaleOutCooldown=0, ScaleInCooldown=300, throttle alarm on ThrottledRequests

## Prompt

Configure DynamoDB auto-scaling for table events-table (arn:
aws:dynamodb:us-east-1:111111111111:table/events-table). The
table is PROVISIONED mode. This is a spiky workload — use
target utilization 50% for both read and write. MinCapacity=20,
MaxCapacity=30000. ScaleOutCooldown=0 (aggressive scale-out),
ScaleInCooldown=300 (conservative scale-in to prevent flapping).
Also create a CloudWatch throttle alarm on ThrottledRequests > 0
sending to SNS arn:aws:sns:us-east-1:111111111111:alerts.
Account ID: 111111111111.
