# Eval: cross-account-replication

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — cross-account replication, destination registry 999999999999, read-only replicas, destination must allow replication

## Prompt

Configure ECR cross-account replication. Source account
111122223333 in us-east-1. Destination account 999999999999
in us-east-1. We are sharing our container images with a
partner account. All repos should replicate. Tags:
Environment=production, Pattern=cross-account.
