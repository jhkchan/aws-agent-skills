# Managed Blockchain Deployer — error handling (moved verbatim from SKILL.md)

> Progressive-disclosure split: this content was moved verbatim from SKILL.md; nothing was rewritten.

## Error handling runbooks

### `create-network` fails with edition error
Operator specified `STARTER`. Starter is retired for new networks.
Change to `STANDARD` and retry.

### Member/node creation hangs in `CREATING`
CA endpoint or node not yet available. Poll `get-member` / `get-node`
every 60 seconds until status is `AVAILABLE` (typically 10-20 min).

### `create-node` fails with VPC/subnet error
The specified AZ has no subnet in the member's VPC. Run
`aws ec2 describe-subnets` to find available AZs, then re-create.

### `fabric-ca-client enroll` fails with connection refused
CA endpoint not yet AVAILABLE. Poll `get-member`. Verify the TLS
certificate was downloaded from the correct S3 path. Verify the
admin password matches member creation.

### Chaincode install fails with lifecycle mismatch
Operator using Fabric 1.4 lifecycle on a 2.x network, or vice versa.
Match the lifecycle to the framework version.

### Ethereum node JSON-RPC returns empty responses
Node is still syncing (hours to days). Check `get-node` status. For
read-only queries during sync, use the Query API instead.

### Query API returns `AccessDeniedException`
IAM role lacks `AmazonManagedBlockchainQueryReadOnly`. Attach the
managed policy or add `managedblockchain-query:*` permissions.

