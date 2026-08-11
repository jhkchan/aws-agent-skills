# Eval: table-target-tracking

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — PROVISIONED table, RCU + WCU scalable targets, target tracking policies at 70%, SLR cited

## Prompt

Configure DynamoDB auto-scaling for table orders-table (arn:
aws:dynamodb:us-east-1:111111111111:table/orders-table). The
table is in PROVISIONED mode. Set up target tracking for both
read and write capacity at 70% utilization. MinCapacity=10,
MaxCapacity=40000 for both RCU and WCU. ScaleOutCooldown=60,
ScaleInCooldown=60. Application auto-scaling service-linked
role is available. Account ID: 111111111111.
