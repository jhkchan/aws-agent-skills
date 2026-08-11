# Eval: client-side-encryption-kms

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — client-side KMS envelope encryption on pii_data column, server-side CMK for encryption at rest, WHERE-clause warning on encrypted columns

## Prompt

Create a table pii_records in keyspace compliance_keyspace.
Columns: record_id (uuid), customer_id (uuid), pii_data (blob),
region (text), created_at (timestamp). Partition key:
(customer_id, region). Clustering key: created_at DESC. The
pii_data column must be encrypted client-side using KMS envelope
encryption with alias/keyspaces-client-encryption. Also use
server-side CMK alias/keyspaces-cmk for encryption at rest.
On-demand capacity. PITR enabled. Region us-east-1. Tags:
Environment=production, Compliance=pii.
