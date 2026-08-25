# NAT Gateway Traffic Optimizer — Diagnostic and Pre-flight Commands

Pre-flight data sources, double-NAT detection, and safety checks moved
verbatim from SKILL.md. Load on demand.

## Required data sources (pre-flight data gate)

**Required data sources** (summarized — see reference for full CLI):
1. NAT Gateway configuration: `aws ec2 describe-nat-gateways`
2. VPC Endpoint inventory: `aws ec2 describe-vpc-endpoints`
3. Route tables: `aws ec2 describe-route-tables` (to detect double-NAT
   and confirm endpoint routes)
4. NAT Gateway CloudWatch metrics (7-30 days):
   `aws cloudwatch get-metric-statistics` for
   `BytesOutToDestination`, `BytesInFromDestination`,
   `BytesOutToSource`, `BytesInFromSource`
5. VPC Flow Logs (7 days): `aws logs start-query` to break down
   traffic by destination service
6. Cost Explorer NAT spend (30 days): `aws ce get-cost-and-usage`
   filtered by `Nat-Gateway` usage type
7. Subnet-to-AZ mapping: `aws ec2 describe-subnets` (for cross-AZ
   analysis)

## Double-NAT detection via route table audit

**Detection via route table audit:**
```bash
# List all route tables in the VPC
aws ec2 describe-route-tables --filter Name=vpc-id,Values=vpc-0abc123 \
  --query 'RouteTables[].{RTB:RouteTableId,Routes:Routes[?DestinationCidrBlock==`0.0.0.0/0`]}' \
  --output json

# Check for chains: does any route table point 0.0.0.0/0 at an
# instance or ENI that is itself behind another NAT?
```

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (create-vpc-endpoint, delete-nat-gateway, replace-route,
  release-address), emit and await operator approval.
- **Back up route tables before changes.** Capture the current route
  table state: `aws ec2 describe-route-tables` and save the output. If
  the optimization needs to be rolled back, the original routes must be
  recoverable.
- **Verify EIP allocation before NAT Gateway deletion.** Note the
  `AllocationId` from `describe-nat-gateways` so the EIP can be released
  after deletion.
- **Test S3/DynamoDB access after Gateway Endpoint creation.** Verify
  that bucket/table policies don't block the endpoint. If policies
  restrict by source IP or VPC, update them to include the endpoint ID.
- **Monitor NAT Gateway metrics for 7 days post-change.** Verify that
  traffic shifted to endpoints and the NAT data processing charge
  dropped accordingly.
- **Bulk-operation limit:** Process at most 3 VPCs per batch. Verify
  each batch before proceeding. Abort if any route table change breaks
  connectivity.
