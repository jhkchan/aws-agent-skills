# Eval: missing-kms-key

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — KMS key alias/nonexistent-key does not exist; cannot reference a nonexistent CMK for encryption at rest

## Prompt

Create a table sensitive_data in keyspace app_keyspace.
Columns: id (uuid), data (blob). Partition key: id. On-demand
capacity. PITR enabled. Use KMS CMK alias/nonexistent-key for
encryption at rest. Region us-east-1.
