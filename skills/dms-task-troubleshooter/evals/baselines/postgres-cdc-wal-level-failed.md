# Baseline (no-skill) response: postgres-cdc-wal-level-failed

This file captures what a generic assistant produces WITHOUT the
dms-task-troubleshooter skill loaded.

---

Your DMS task TASK001 failed. The error message says "logical decoding
requires wal_level >= logical." This means your PostgreSQL source is
not configured for logical replication.

You should check your PostgreSQL settings and enable logical
replication. You may also want to restart the task once you've fixed
the configuration.
