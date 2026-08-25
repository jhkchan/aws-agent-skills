# Neptune Graph Deployer — Error Handling

Provisioning and runtime error deep dives moved verbatim from SKILL.md.
Load on demand.

## Symptom index (moved from SKILL.md)

### Cluster creation fails with "encryption not supported"

- Verify the engine version and instance type support encryption. All
  current Neptune instance types support storage encryption.

### Clients cannot connect to the cluster

- Check the security group allows inbound from the application SG on
  port 8182. Verify `neptune_enforce_ssl=1` requires clients to use TLS
  (wss:// for Gremlin, https:// for SPARQL).

### Read replicas lagging behind primary

- Check instance type — replicas should match the primary's type. Monitor
  `NeptuneReadReplicaLag` in CloudWatch. If lag is persistent, upgrade
  the replica instance type or reduce write throughput.

### Neptune Streams returning no records

- Verify `neptune_streams=1` in the parameter group and that the primary
  instance has been rebooted since the change. Streams only capture
  changes after enablement.

### Global Database replication failing

- Verify engine versions match across primary and secondary regions.
  Check the secondary cluster's security group and subnet group are
  correctly configured.

### Bulk loader errors

- Verify the S3 bucket is in the same region as the Neptune cluster.
  Check the IAM role has `s3:GetObject` and `s3:ListBucket` permissions.
  Use `mode: RESUME` to retry partial loads.
