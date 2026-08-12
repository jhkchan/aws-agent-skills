# Eval: schema-change-in-green

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — Blue/Green with schema change and parameter group change in green, blue frozen, green validation step

## Prompt

Create an RDS Blue/Green Deployment for my RDS MySQL instance
prod-orders-db (mysql 8.0.35) in us-east-1, account 123456789012.
Same engine version 8.0.35. I need to apply a schema change in
green: ALTER TABLE orders ADD COLUMN status_code INT DEFAULT 0.
Also apply parameter group prod-mysql80-tuned. Application has
retry logic. Tags: Environment=production,
Change=schema-and-params.
