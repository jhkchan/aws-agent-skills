# RDS Connectivity Troubleshooter — diagnostic commands (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

### Step 0: Pre-flight — gather instance and client state (moved from SKILL.md)

```bash
# 1. Instance / cluster metadata
aws rds describe-db-instances --db-instance-identifier <id> \
  --output json | jq('.DBInstances[0] | {DBInstanceStatus,
    StorageStatus, Endpoint, DBSubnetGroup: .DBSubnetGroup.SubnetGroupStatus,
    SGs: [.VpcSecurityGroups[] | .VpcSecurityGroupId],
    Engine, EngineVersion, DBInstanceClass, AllocatedStorage,
    MaxAllocatedStorage, StorageAutoScalingEnabled, MultiAZ,
    IAMAuth: .IAMDatabaseAuthenticationEnabled}')

# 2. Recent events (failover, maintenance, storage-full)
aws rds describe-events --source-type db-instance \
  --source-identifier <id> --duration 360 --output json | \
  jq('.Events[:20] | [.[] | {Date: .Date, Message: .Message}]')

# 3. Aurora cluster (if applicable) — endpoints, writer, readers
aws rds describe-db-clusters --db-cluster-identifier <cluster> \
  --output json | jq('.DBClusters[0] | {Status, Endpoint,
    ReaderEndpoint, MultiAZ, Engine, Members: [.DBClusterMembers[] |
    {DBInstanceIdentifier, IsClusterWriter, DBClusterParameterGroupStatus}]}')

# 4. Client-side network context (run from the client host or its VPC)
#    - Subnet, AZ, security group of the EC2 / ECS / Lambda caller
#    - Route table, NACL for the client subnet
#    - DNS resolver (Route 53 Resolver, on-prem DNS, cross-region)
```

## Pre-flight safety checks (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`modify-db-instance`, `authorize-security-group-ingress`,
  `modify-db-cluster`, `reboot-db-instance`), emit and await operator
  approval.
- **Read-only first.** Every probe in the diagnostic tree is read-only.
- **Modifying an instance** triggers a brief connection drop in some
  cases (especially for parameter group changes that require a reboot).
  Confirm during a maintenance window.
- **Enabling storage auto-scaling** is non-disruptive; the storage
  expands in the background.
- **Failover** (`reboot-db-instance --force-failover`) is disruptive —
  the writer changes and the application must reconnect via the
  cluster endpoint.
- **Security group changes** propagate within seconds but can briefly
  drop in-flight connections.
- **Bulk remediation batch limit.** When the same root cause affects
  multiple instances, batch into groups of at most 5 and verify.

