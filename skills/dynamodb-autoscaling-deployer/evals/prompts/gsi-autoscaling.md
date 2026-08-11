# Eval: gsi-autoscaling

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — GSI scalable targets with resource-id table/<name>/index/<gsi>, dynamodb:index dimensions

## Prompt

Configure DynamoDB auto-scaling for the GSI status-index on
table orders-table (arn:aws:dynamodb:us-east-1:111111111111:
table/orders-table). The table is in PROVISIONED mode. The
table already has auto-scaling configured; I need GSI
auto-scaling for status-index. Target utilization 70%.
MinCapacity=5, MaxCapacity=20000 for both RCU and WCU.
Cooldowns 60s each. Account ID: 111111111111.
