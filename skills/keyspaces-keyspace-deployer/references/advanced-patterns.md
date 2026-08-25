# Advanced Patterns — Amazon Keyspaces Keyspace Deployer

Edge-case guidance, VPC endpoint private access, and recent AWS features moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Step 9 — VPC endpoint for private access (moved from SKILL.md)

For private network access (no internet traversal), create an interface
VPC endpoint for Keyspaces using AWS PrivateLink.

```bash
# Create an interface VPC endpoint for Keyspaces
VPCE_ID=$(aws ec2 create-vpc-endpoint \
  --vpc-id vpc-aaa11122 \
  --service-name com.amazonaws.us-east-1.cassandra \
  --subnet-ids subnet-aaa111 subnet-bbb222 \
  --security-group-ids sg-keyspaces-client \
  --vpc-endpoint-type Interface \
  --private-dns-enabled \
  --query 'VpcEndpoints[0].VpcEndpointId' --output text)

echo "VPC Endpoint: $VPCE_ID"
```

**Critical:** `--private-dns-enabled` is REQUIRED for the Cassandra
driver to resolve the Keyspaces endpoint to the private IP. Without it,
the driver resolves to the public IP and traffic traverses the internet.

**Security group:** the VPC endpoint security group must allow inbound
TCP 9142 from the application subnets.

## Step 12 — Recent features (moved from SKILL.md)

**Recent AWS features (2023-2026):**

- **Client-side encryption support (2023-2024):** AWS published the
  Amazon Keyspaces client-side encryption library, providing envelope
  encryption via KMS for field-level encryption transparent to the
  Keyspaces service.

- **Auto-scaling improvements (2023-2024):** Enhanced auto-scaling for
  provisioned tables with faster scale-out (60s cooldown) and more
  responsive target tracking.

- **VPC endpoint private DNS (2023-2024):** Private DNS for Keyspaces
  VPC endpoints is now generally available, enabling seamless private
  access without certificate changes.

- **Schema management API (2024-2025):** The Keyspaces API now supports
  full table schema management (create, update, delete) without
  requiring CQL access, simplifying infrastructure-as-code workflows.

- **Multi-region replication (2024-2025):** Keyspaces multi-region
  replication (similar to DynamoDB Global Tables) became available in
  select regions, enabling cross-region active-active deployments.

- **Cost optimization for on-demand (2025-2026):** Tiered pricing for
  on-demand capacity at high volumes, reducing per-RU cost for
  workloads exceeding 1 billion RUs per month.

