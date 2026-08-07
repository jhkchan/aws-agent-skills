# Eval prompt: too-many-connections-aurora-derived

Diagnose the connectivity failure for the following Aurora MySQL cluster.
Walk the diagnostic tree and emit the standard diagnostic block (TARGET,
VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: application cannot open new connections to the Aurora MySQL
writer. Error from the engine: `Too many connections`. Existing
connections continue to work.

DBClusterIdentifier: db-too-many-connections-aurora
Engine: aurora-mysql
Status: available
Endpoint: db-too-many-connections-aurora.cluster-on.aws:3306
Writer instance class: db.r6i.large
Threads_connected: 6000
max_connections: 6000 (derived from db.r6i.large)

Notes:
  - A parameter-group override attempted to set max_connections = 8000
    but the engine continues to report 6000.
  - No maintenance events, no failover events in the last hour.
  - Security groups, NACLs, and route tables are unchanged from the
    known-good baseline.
