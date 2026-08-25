# Error Handling — ElastiCache Cluster Deployer

Provisioning failure triage moved verbatim from SKILL.md. Loaded on demand.

## Error handling — provisioning failure triage (from SKILL.md)

### Cluster creation fails with "encryption not supported"

- Verify the engine version supports encryption (Redis >= 6.x for TLS
  1.3). Upgrade the engine version and retry.

### Multi-AZ failover not triggering

- Verify at least one replica per shard. Check nodes are across >= 2
  AZs. Use `describe-replication-groups` to confirm `AutomaticFailover`
  status is "enabled."

### Clients cannot connect

- Check the security group allows inbound from the app SG on the
  correct port. For TLS-enabled clusters, verify the client library
  supports TLS connections.

### Online resharding stuck in "modifying"

- Resharding is asynchronous (minutes to hours). Monitor with
  `describe-replication-groups`. Check CloudWatch for replication lag
  or memory pressure if stuck.

### Snapshot skipped

- Snapshot window overlaps maintenance window. Reschedule one of them.
