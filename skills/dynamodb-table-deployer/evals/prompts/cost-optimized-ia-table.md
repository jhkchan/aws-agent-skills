# Eval: cost-optimized-ia-table

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — cold archive on Standard-IA, TTL for 3-year retention

## Prompt

Provision a DynamoDB table named "historical-orders-archive" in
us-east-1 for archived order data (3-year retention). Traffic is
very low (a few queries per week from BI). Use the most
cost-effective table class. Items DO expire at 3 years via TTL on
"retainUntil". Use SSE-KMS with customer CMK alias/archive-kms-key.
No GSI needed (single access pattern by orderId). PITR on for safety.
Deletion protection on. Tags: Environment=production,
Workload=archive. Account ID: 123456789012.
