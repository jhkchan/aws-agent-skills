# Eval: missing-subnet-group-and-acl

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — subnet group (Multi-AZ requires multi-AZ subnet group), security group (port 6379 inbound), and named ACL (MemoryDB requires an ACL; default open-access NOT for production) all unspecified

## Prompt

Help me create a new MemoryDB for Redis cluster called "session-db"
in us-east-1. I want Multi-AZ failover for durability. We will
store user session data. Region: us-east-1, Account: 123456789012.
