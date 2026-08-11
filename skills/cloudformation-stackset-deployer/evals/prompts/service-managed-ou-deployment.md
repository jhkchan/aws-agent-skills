# Eval: service-managed-ou-deployment

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — SERVICE_MANAGED, OU targeting, multi-region, managed execution, CAPABILITY_IAM

## Prompt

Create a CloudFormation StackSet named baseline-iam-roles
using the SERVICE_MANAGED permission model. Target OU
ou-abc-12345678 (Security OU) across regions us-east-1,
us-west-2, and eu-west-1. Template is at
s3://my-bucket/templates/baseline-iam.yaml (18,432 bytes).
Capabilities: CAPABILITY_IAM. Parameters:
Environment=production,
AuditRoleArn=arn:aws:iam::111111111111:role/audit.
Organizations trusted access is already enabled. Enable
managed execution. Tags: Owner=platform, CostCenter=infra.
Account ID: 111111111111.
