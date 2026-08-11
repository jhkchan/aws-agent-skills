# Eval: missing-subnet-group-and-cmk

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — subnet group (Multi-AZ requires multi-AZ subnet group), security group (port 8182 inbound), and customer CMK ARN all unspecified

## Prompt

Help me create a new Neptune DB cluster called "user-graph" in
us-east-1. I want Multi-AZ failover and a customer-managed CMK for
encryption. We will store user-relationship data. Region: us-east-1,
Account: 123456789012.
