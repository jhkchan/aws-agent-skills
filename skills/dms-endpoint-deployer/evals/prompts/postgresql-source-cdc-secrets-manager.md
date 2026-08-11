# Eval: postgresql-source-cdc-secrets-manager

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — PostgreSQL source with pglogical plugin, Secrets Manager credentials, verify-full SSL, KMS encryption, wal_level=logical prerequisite verified

## Prompt

Create a DMS source endpoint for PostgreSQL at
prod-db.cluster-abc123.us-east-1.rds.amazonaws.com port 5432,
database "analytics", us-east-1. Use Secrets Manager secret
arn:aws:secretsmanager:us-east-1:123456789012:secret:dms-pg-prod.
SSL mode verify-full with certificate prod-ca-cert. CDC enabled
with pglogical plugin, slot name dms_replication_slot. KMS key
arn:aws:kms:us-east-1:123456789012:key/abc123. Replication
instance rep-instance-prod. Tags: Environment=production,
MigrationType=cdc.
