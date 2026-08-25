# Error Handling — ElastiCache Cache Deployer

Provisioning failure triage moved verbatim from SKILL.md. Loaded on demand.

## Error handling — provisioning failure triage (from SKILL.md)

### Cluster name already exists (`ReplicationGroupAlreadyExists`)

```bash
aws elasticache describe-replication-groups --replication-group-id <name>
```

- If configuration matches intent: the cluster is already provisioned
  correctly. Skip to verification and emit READY_TO_DEPLOY.
- If configuration differs: decide whether to `modify-replication-group`
  (mutable settings: node type, parameter group, snapshots, maintenance
  window, security groups, AUTH token) or create a NEW cluster.
  Engine, cluster-mode, and at-rest-encryption CANNOT be changed
  post-creation — those require a new cluster + client repoint.

### Multi-AZ create fails (`CacheSubnetGroup does not span multiple AZs`)

The subnet group has all subnets in one AZ. Multi-AZ Redis requires
the subnet group to span at least 2 AZs.

**Fix:**

```bash
# Add a subnet in a different AZ to the subnet group
# (ElastiCache does not allow removing subnets, only adding)
aws elasticache modify-cache-subnet-group \
  --cache-subnet-group-name prod-cache-subnet \
  --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc   # now spans >=2 AZs
```

**Verify** with `aws ec2 describe-subnets --subnet-ids ...` — confirm
distinct `AvailabilityZone` values.

### AUTH enable fails (`Encryption in transit is not enabled`)

AUTH requires TLS. Without `--transit-encryption-enabled=true`,
ElastiCache rejects `--auth-token`.

**Fix:** enable both together:

```bash
aws elasticache modify-replication-group \
  --replication-group-id prod-cache \
  --auth-token "$(aws secretsmanager get-secret-value ...)" \
  --transit-encryption-enabled true \
  --apply-immediately
```

Note: enabling TLS post-creation triggers a rolling node replacement
that disconnects every client for 30-90 seconds per node. Plan a
maintenance window.

### Snapshot restore creates cluster with wrong node type

Snapshot restore uses the node type specified at restore time, NOT the
source's node type. Verify `--cache-node-type` on the
`create-replication-group` call.

```bash
aws elasticache create-replication-group \
  --replication-group-id prod-cache-restored \
  --cache-node-type cache.r6g.2xlarge \   # specify explicitly
  --snapshot-arns arn:aws:elasticache:...:snapshot:prod-cache-snap
```

### Cluster stuck in `MODIFYING` after `apply-immediately`

A rolling node replacement on a large cluster (many shards + replicas)
can take 30+ minutes. Use `--apply-immediately` only for emergencies;
otherwise schedule modifications in the maintenance window.

```bash
aws elasticache describe-replication-groups --replication-group-id <name> \
  --query 'ReplicationGroups[0].Status'
# Wait for "available" before issuing the next modify.
```

### Cluster mode enabled → disabled migration is NOT a modify

There is NO `modify-replication-group` flag to switch cluster mode.
Migration requires:

1. Create a NEW replication group with `--num-node-groups 1`
   (cluster mode disabled equivalent) or no cluster config.
2. Repoint clients to the new endpoint.
3. Delete the old cluster.

NEVER attempt to "downgrade" cluster mode by reducing shard count to
1 — the cluster remains in cluster-mode-enabled state.
