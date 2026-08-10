# Eval: missing-vpc-and-kms

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — VPC subnets, security group, KMS key ARN, and master IAM role all required for production-grade domain

## Prompt

Help me create a new OpenSearch domain called "logs-search" in
us-east-1. I want it to be production-grade — encryption at rest,
VPC-only access, fine-grained access control. We will index application
logs. Region: us-east-1, Account: 123456789012.
