# Eval: standard-ledger-verification

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — STANDARD permissions mode, deletion protection enabled, KMS customer-managed key, tables and indexes defined, hash chain verification workflow documented

## Prompt

Create a QLDB ledger named audit-ledger in us-east-1. Permissions
mode STANDARD. Enable deletion protection. KMS key
arn:aws:kms:us-east-1:123456789012:key/abc123. Tables: transactions,
accounts, audit_log. Indexes on transactions(transactionId,
fromAccount) and accounts(accountId). Tags: Environment=production,
Application=audit, Compliance=SOX.
