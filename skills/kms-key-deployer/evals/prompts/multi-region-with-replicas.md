# Eval: multi-region-with-replicas

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — multi-Region primary + replicas in us-west-2 + eu-west-1

## Prompt

Provision a multi-Region customer-managed KMS key for
cross-Region disaster recovery in us-east-1. Alias:
alias/dr-cmk (primary). Replicate to us-west-2 and eu-west-1.
Workload: encrypt DynamoDB global tables data. Key spec:
SYMMETRIC_DEFAULT. Key administrators: kms-admin role. Key
users: the dr-service IAM role (in each Region). Deletion
window: 30 days. Tags: Environment=production,
Application=dr. Account: 123456789012.
