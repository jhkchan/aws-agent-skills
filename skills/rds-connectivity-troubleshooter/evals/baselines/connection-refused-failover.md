# Baseline (no-skill) response: connection-refused-failover

---

The cluster is currently modifying, which suggests a failover is in
progress. The "server closed the connection unexpectedly" error is
expected during a Multi-AZ failover. You should wait a minute or two for
the failover to complete, then retry the connection.

If the issue persists, you may need to restart your application to clear
stale connections.
