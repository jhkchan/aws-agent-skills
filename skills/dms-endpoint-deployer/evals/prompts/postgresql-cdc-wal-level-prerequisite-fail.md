# Eval: postgresql-cdc-wal-level-prerequisite-fail

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — PostgreSQL CDC requires wal_level=logical but source has wal_level=replica

## Prompt

Create a DMS source endpoint for PostgreSQL at
staging-db.example.com port 5432, database "staging", us-east-1.
Enable CDC with pglogical plugin. The source database has
wal_level=replica. Replication instance rep-instance-prod.
Tags: Environment=staging.
