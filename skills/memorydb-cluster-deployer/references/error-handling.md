# MemoryDB Cluster Deployer — error handling (moved verbatim from SKILL.md)

> Progressive-disclosure split: this content was moved verbatim from SKILL.md; nothing was rewritten.

## Error handling runbooks

### Cluster name already exists (`ClusterAlreadyExists`)

- If config matches intent: skip to verification, emit READY_TO_DEPLOY.
- If config differs: mutable settings (node type, shard count, replica
  count, parameter group, snapshot retention, security groups, ACL)
  change via `update-cluster`. TLS, data tiering, and VPC/subnet
  placement CANNOT be changed — those require a new cluster +
  snapshot/restore.

### Multi-AZ create fails (`SubnetGroup does not span multiple AZs`)

**Fix:** add subnets in different AZs via `update-subnet-group`, then
verify distinct `AvailabilityZone` values via `aws ec2 describe-subnets`.

### ACL auth fails (`NOAUTH` from client)

**Fix:** verify the cluster's ACL includes the user via
`aws memorydb describe-acls`; verify the client sends
`AUTH <username> <password>` on connect (most modern Redis drivers do
this automatically when configured with credentials).

### Data tiering enable fails (`DataTiering cannot be enabled`)

Data tiering requires `db.r6gd` AND `--data-tiering=true` at creation.
A cluster created without tiering CANNOT be tiered later.

**Fix:** create a NEW cluster with `db.r6gd.<size>` and
`--data-tiering=true`, then migrate via snapshot/restore or
dual-write cutover.

