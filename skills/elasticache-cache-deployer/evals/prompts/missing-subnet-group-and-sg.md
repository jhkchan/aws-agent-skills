# Eval: missing-subnet-group-and-sg

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — subnet group (Multi-AZ requires multi-AZ subnet group), security group (cache port inbound), and AUTH details all unspecified

## Prompt

Help me create a new ElastiCache Redis cluster called "orders-cache"
in us-east-1. I want Multi-AZ with failover and AUTH enabled. We will
cache order data — should be pretty simple. Region: us-east-1,
Account: 123456789012.
