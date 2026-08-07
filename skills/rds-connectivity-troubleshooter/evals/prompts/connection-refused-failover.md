# Eval prompt: connection-refused-failover

Diagnose the connectivity failure for the following Aurora PostgreSQL
cluster. Walk the diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: application cannot connect to the Aurora PostgreSQL writer
endpoint. Error: `server closed the connection unexpectedly`. Connections
to the reader endpoint also fail intermittently. The page started
~45 seconds ago.

DBClusterIdentifier: db-connection-refused-failover
Engine: aurora-postgresql
Status: modifying
Endpoint: db-connection-refused-failover.cluster-on.aws:5432
MultiAZ: true
DBClusterMembers: writer flipped 45 seconds ago (instance-A demoted,
  instance-B promoted)
Recent events (last 5 minutes):
  - "Multi-AZ failover started" (45 seconds ago)

No SG/NACL/route changes in the last 24 hours. The application connects
to the cluster writer endpoint, not an instance endpoint.
