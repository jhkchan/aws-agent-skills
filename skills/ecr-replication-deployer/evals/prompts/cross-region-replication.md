# Eval: cross-region-replication

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — registry-level cross-region replication, ALL repos replicate, read-only replicas, 3x storage cost noted

## Prompt

Configure ECR cross-region replication for account
111122223333. Source region us-east-1. Destination regions
us-west-2 and eu-west-1. We need DR coverage across three
regions. All repos should replicate. Tags:
Environment=production, Pattern=dr.
