# Eval: on-demand-vs-provisioned

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — table is ON-DEMAND, skill advises switch to PROVISIONED first, then configures auto-scaling

## Prompt

I want to set up DynamoDB auto-scaling on table users-table
(arn:aws:dynamodb:us-east-1:111111111111:table/users-table).
The table is currently ON-DEMAND. Target utilization 70%,
MinCapacity=5, MaxCapacity=10000 for both RCU and WCU.
Cooldowns 60s. Account ID: 111111111111.
