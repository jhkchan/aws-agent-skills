# Baseline (no-skill) response: database-replatform-dms

This file captures what a generic assistant produces WITHOUT the
migration-hub-strategy-deployer skill loaded.

---

For the Oracle 11g to Aurora PostgreSQL migration, you can use DMS to
replicate the data. Set up the source and target endpoints in DMS and
create a migration task with full-load-and-cdc.

You already have the DMS replication instance provisioned, so you just
need to configure the endpoints and start the task.

After the data is replicated, update your application connection strings
to point to the Aurora cluster.
