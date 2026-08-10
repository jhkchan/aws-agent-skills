# Baseline (no-skill) response: jdbc-connection-missing-security-group

This file captures what a generic assistant produces WITHOUT the
glue-job-troubleshooter skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT + CATEGORY, four-rule
network path, self-referencing SG rule, nc verification probe).

---

The Glue job failed with a VPC Connection error trying to reach your
PostgreSQL database. The error usually means a network issue. Check
that the database is reachable from the Glue subnet, and verify the
security groups on both ends allow traffic on port 5432.

You should also confirm the Glue connection has the right subnet and
that route tables are set up correctly.
