# Configuration Patterns

## Common Patterns

1. Multi-AZ with failover
2. Encryption (KMS + TLS)
3. Security group rules
4. Backup and restore
5. Monitoring via CloudWatch

See SKILL.md for full decision tree and NEVER patterns.

## Expert heuristic: cluster mode topology, promotion priority, window overlap (from SKILL.md)

A baseline model says "create a Redis cluster." The correct heuristic
designs the cluster-mode topology (shards and hash slots), sets replica
promotion priorities for predictable failover, and ensures the snapshot
window does not overlap the maintenance window.

```text
Cluster mode enabled — 3 shards, 1 replica each (6 nodes total):

  Shard 1 (slots 0-5460):
    Primary: node-0001 (AZ-a)
    Replica: node-0004 (AZ-b, priority 100) ← failover target

  Shard 2 (slots 5461-10922):
    Primary: node-0002 (AZ-b)
    Replica: node-0005 (AZ-c, priority 100)

  Shard 3 (slots 10923-16383):
    Primary: node-0003 (AZ-c)
    Replica: node-0006 (AZ-a, priority 100)

Replica promotion priority (ReplicaPriority, default 100):
  Lower number = higher promotion priority.
  Priority 0 = never promoted (read-only replica).

Failover: primary fails → highest-priority replica promoted → DNS updated.
```

**Window overlap check:**
```text
Snapshot window:   03:00-05:00 UTC daily
Maintenance window: mon:05:00-mon:06:00 UTC weekly

If they overlap → snapshots skipped or maintenance delayed.
Best practice: gap of 1+ hours between snapshot end and maintenance.
  Snapshot:   01:00-03:00 UTC
  Maintenance: mon:05:00-mon:06:00 UTC
```

**Key implication:** the topology (shard count, replica count, AZ
placement) determines capacity and availability. Replica promotion
priority controls failover behavior. Window overlap is a silent failure
that causes missing backups.
