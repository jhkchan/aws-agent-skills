# Error Handling — Amazon Keyspaces Keyspace Deployer

API error tables and failure-mode deep dives moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Error handling (moved from SKILL.md)

### Table creation fails with "ValidationException"
- The schema definition is malformed. Verify the partition key columns
  match columns in `allColumns`. Verify column types are valid CQL
  types. Verify clustering key `orderBy` is ASC or DESC.

### Connection fails with "SSL handshake error"
- Port mismatch: Keyspaces requires port 9142 (not 9042). Verify the
  driver connects to `cassandra.<region>.amazonaws.com:9142` with SSL
  enabled and the AmazonRootCA1.pem certificate.

### Connection fails with "Authentication failed"
- SigV4 authentication error: verify IAM credentials are valid and the
  IAM policy includes `cassandra:Select` (for reads) and
  `cassandra:Modify` (for writes) on the keyspace/table resource.

### Throttling (WriteTimeout/ReadTimeout)
- Provisioned capacity is too low. Enable auto-scaling (Step 11) or
  switch to on-demand capacity. Monitor `ConsumedWriteCapacityUnits` and
  `ConsumedReadCapacityUnits` to right-size.

### VPC endpoint connection fails
- Private DNS not enabled: verify `--private-dns-enabled` on the VPC
  endpoint. Security group: verify inbound TCP 9142 from the
  application subnets. Subnet: verify the endpoint is in the correct
  subnets.

### PITR restore fails
- PITR was not enabled on the table. Verify PITR status with
  `get-table`. PITR must have been enabled for at least 5 minutes
  before the restore point.

