# Baseline (no-skill) response: aurora-unplanned-failover

This file captures what a generic assistant produces WITHOUT the
dr-failover-automator skill loaded.

---

For an unplanned Aurora Global failover during a region outage, you'll
need to manually promote the secondary cluster. Use the
`remove-from-global-cluster` command to detach the secondary and make
it a standalone writable cluster.

After promotion, update Route 53 to point at the new writer endpoint
in us-west-2. Then verify your application can read and write.

Once us-east-1 comes back, you'll need to rebuild the global cluster
since the old primary can't rejoin. Take a snapshot of the new primary
and create a new global cluster.

Document the steps in a runbook and test with a game-day drill.
