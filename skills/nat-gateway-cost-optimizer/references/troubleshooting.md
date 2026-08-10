# NAT Gateway Cost Optimizer Troubleshooting and Edge Cases

Load this reference when an optimisation step fails, when CLI calls
error out, or when the VPC has unusual topology (TGW, peering,
private-only) that the standard flow does not cover.

## Remediation procedure failures

These branches describe what to do when a step in the optimisation
procedure itself fails — not when a CLI call errors out, but when the
optimisation *logic* cannot proceed safely.

- **If `create-vpc-endpoint` (Interface) fails with
  `ServiceLimitExceeded` for ENIs per subnet:** The VPC has hit the
  per-subnet ENI cap (default varies by instance type and subnet
  size). Do NOT retry in a different AZ — the limit is account+subnet
  scoped. Remediation: (a) request a quota increase via
  `service-quotas request-service-quota-increase --service-code vpc
  --quota-code L-FE5A380F`, OR (b) fall back to a Gateway endpoint
  for S3/DynamoDB and defer the Interface endpoint until the quota is
  approved. Surface the blocked recommendation as `VERDICT:
  QUOTA_BLOCKED` with the quota name and current/applied values.

- **If the Gateway endpoint does not cover the required S3 bucket
  (same-region access expected but bucket is in a different
  partition or the access path is non-S3):** Gateway endpoints only
  cover S3 and DynamoDB in the same region and same partition. If the
  workload accesses S3 Object Lambda, S3 access points in another
  account, or uses SDK calls that bypass the endpoint DNS (custom
  endpoints, Direct Connect public VIF), the Gateway endpoint
  silently does NOT intercept the traffic. Detect by re-running the
  Flow Logs query after endpoint creation — if NAT data-processing
  bytes do not drop by the expected delta, the endpoint is not
  capturing the traffic. Remediation: an Interface endpoint for
  `com.amazonaws.<region>.s3` (covers all S3 API calls including
  access points), OR a route-table audit for custom DNS.

- **If the NAT Gateway has active connections during replacement
  (single-NAT-to-dual-NAT migration or AZ topology change):**
  Existing TCP connections through the old NAT Gateway will be reset
  when its ENI is deleted. Detection: `aws ec2
  describe-network-interfaces --filters Name=description,Values='ELB
  managed NAT gateway ...'` and CloudWatch
  `NATGateway.BytesOutToDestination`. Remediation: do NOT delete the
  old gateway until connection count is zero. Add the new gateway to
  the route table, wait one TTL cycle (default 350s for established
  TCP, longer for long-lived sessions), verify new connections use
  the new gateway via Flow Logs, then delete the old one. For
  stateful workloads (long-lived WebSocket, RDS sessions), schedule a
  maintenance window — connection reset is unavoidable.

- **If the Elastic IP release fails after NAT Gateway deletion
  (`InvalidAddress.AllocationInUse` or stuck in `pending`):** The
  EIP remains associated with the now-deleted gateway ENI. Poll
  `aws ec2 describe-addresses --public-ips <ip>` until
  `AssociationId` is empty (can take 5-30 minutes). If still
  associated after 30 minutes, open an AWS Support case — do NOT
  force-disassociate, the ENI cleanup is asynchronous. The EIP
  charge accrues during this window; surface as `VERDICT:
  CLEANUP_PENDING` with expected completion time.

- **If Cost Explorer returns `NatGateway` cost but Flow Logs show no
  matching traffic (cost/traffic delta > 20%):** Either the Flow
  Logs query is wrong (wrong ENI filter, wrong time window) or there
  is a second NAT Gateway in the VPC. Re-query `aws ec2
  describe-nat-gateways --filter Name=vpc-id,Values=<vpc>` and
  aggregate all gateway costs. Do NOT proceed with the
  recommendation until the cost/traffic reconciliation is within 20%.

## Edge cases

- **Transit Gateway + NAT Gateway interaction.** When a VPC is
  attached to a Transit Gateway (TGW) that routes egress through a
  central egress VPC ("hub-and-spoke"), the spoke VPC's NAT Gateway
  is NOT used for cross-VPC traffic — TGW routes override local
  `0.0.0.0/0` routes for destinations reachable via TGR. Detection:
  query `aws ec2 search-transit-gateway-routes` and look for
  `0.0.0.0/0` or specific CIDR entries pointing to a TGW attachment.
  Implication: a spoke NAT Gateway with low traffic may be a
  candidate for deletion, BUT verify the egress VPC's NAT is sized
  for the aggregate spoke traffic. The optimisation must run at the
  egress VPC, not the spoke. Surface as a finding:
  `TGW_EGRESS_CENTRALIZED — spoke NAT traffic low, evaluate spoke NAT
  removal; run optimisation on <egress-vpc>`.

- **VPC with only private subnets and no internet gateway.** A NAT
  Gateway cannot be created (requires an IGW). Such VPCs already
  have optimal egress via Gateway endpoints for S3/DynamoDB. If
  non-S3 traffic is required, the workload must use Interface
  endpoints or a TGW egress path. Skip NAT cost optimisation;
  verdict `ALREADY_OPTIMAL (no NAT present, IGW not attached)`.

- **NAT Gateway in a VPC peered with another VPC.** VPC peering does
  NOT route traffic through a NAT Gateway in the peer — peering
  routes are direct subnets. If the peer VPC has no NAT and depends
  on the local NAT for egress, that traffic will NOT appear in local
  NAT Flow Logs. Detection: check peering connection route tables.
  Surface as a finding if a peer VPC's egress strategy is missing.

## CLI and data-source failure modes

| Failure mode | Detection | Handling |
|---|---|---|
| `describe-nat-gateways` returns empty | `len(NatGateways) == 0` | VPC has no NAT Gateway. Verdict ALREADY_OPTIMAL. |
| `get-cost-and-usage` returns $0 for NatGateway | Cost is 0 | Either no NAT Gateway or no traffic. Verify with `describe-nat-gateways`. |
| VPC Flow Logs query returns empty results | `queryResults` empty | Flow Logs not enabled or querying wrong ENI. Fall back to Cost Explorer service-level data; flag Interface endpoint recommendations as MEDIUM confidence. |
| `create-vpc-endpoint` fails with `RouteConflict` | API error | A route in the specified route table already points to a different endpoint. Remove the conflicting route first, or use a different route table. |
| `create-vpc-endpoint` (Interface) fails with `PrivateDnsOptionsIncompatible` | API error | The VPC already has a conflicting private DNS configuration. Retry with `--no-private-dns-enabled` and surface the DNS resolution impact. |
| `delete-nat-gateway` fails with `NatGatewayNotFound` | API error | The gateway was already deleted or is in a different region. Re-query with the correct region. |
| `release-address` fails with `AddressInUse` | API error | The EIP is still associated with the NAT Gateway (deletion not yet complete). Wait for the NAT Gateway state to reach `deleted`, then retry. |
