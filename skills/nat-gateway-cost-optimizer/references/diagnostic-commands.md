# NAT Gateway Cost Optimizer — Diagnostic and Pre-flight Commands

Load this reference before classification (the VPC metadata gate) and before
any remediation CLI (the safety checks). Content moved verbatim from SKILL.md.

## Pre-flight: VPC metadata gate

Run before classification. Misclassifying these produces false positives.

**Live-account pre-flight (skip if offline audit):**

```bash
# 1. Enumerate NAT Gateways and their state
aws ec2 describe-nat-gateways --filter "Name=vpc-id,Values=<vpc-id>" \
  --output json | jq '.NatGateways[] | {
    nat_gateway_id: .NatGatewayId,
    state: .State,                        # "available" | "pending" | "deleting"
    subnet_id: .SubnetId,                 # identifies the AZ
    public_ip: .NatGatewayAddresses[0].PublicIp,
    private_ip: .NatGatewayAddresses[0].PrivateIp
  }'

# 2. Enumerate existing VPC endpoints
aws ec2 describe-vpc-endpoints --filter "Name=vpc-id,Values=<vpc-id>" \
  --output json | jq '.VpcEndpoints[] | {
    endpoint_id: .VpcEndpointId,
    type: .VpcEndpointType,               # "Gateway" | "Interface" | "GatewayLoadBalancer"
    service: .ServiceName,
    state: .State,
    subnet_ids: .SubnetIds,
    route_table_ids: .RouteTableIds
  }'

# 3. Pull NAT Gateway data-processing cost from Cost Explorer (last 30 days)
aws ce get-cost-and-usage \
  --time-period Start=2026-07-01,End=2026-08-01 \
  --granularity MONTHLY \
  --filter '{"Dimensions":{"Key":"USAGE_TYPE_GROUP","Values":["EC2: NatGateway"]}}' \
  --metrics "UsageQuantity" "AmortizedCost" \
  --group-by Type=DIMENSION,Key=USAGE_TYPE \
  --output json

# 4. Pull per-service traffic breakdown via VPC Flow Logs (last 7 days)
aws logs start-query \
  --log-group-name <flow-logs-group> \
  --start-time $(date -d '-7 days' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, interface-id, srcaddr, dstaddr, bytes
    | filter interface-id = "<eni-of-nat-gateway>"
    | stats sum(bytes) as total_bytes by dstaddr
    | sort total_bytes desc
    | limit 20'

# 5. Enumerate route tables to confirm which subnets route to which NAT
aws ec2 describe-route-tables \
  --filter "Name=vpc-id,Values=<vpc-id>" \
  --output json | jq '.RouteTables[] | {
    route_table_id: .RouteTableId,
    subnet_id: (.Associations[0].SubnetId // "main"),
    nat_gateway: ([.Routes[] | select(.NatGatewayId != null) | .NatGatewayId][0])
  }'
```

### Data-quality short-circuits

| Condition | Effect on optimisation |
|---|---|
| Cost Explorer returns $0 NAT Gateway cost | VPC has no NAT Gateway spend. Verdict ALREADY_OPTIMAL for this VPC. |
| VPC Flow Logs not enabled on the VPC | Cannot quantify per-service traffic breakdown. Fall back to Cost Explorer service-level filter; flag Interface endpoint recommendations as MEDIUM confidence (traffic volume estimated, not measured). |
| NAT Gateway state `pending` or `deleting` | Transient state. Re-query after 5 minutes; do not optimise against a gateway that is not yet serving traffic. |
| Route table shows no route to the NAT Gateway for a private subnet | That subnet's traffic does not flow through NAT; its GB do not count toward NAT processing. Verify the route-table-to-subnet mapping before aggregating traffic. |
| VPC has no private subnets (all public) | NAT Gateway is unused. Surface as a topology finding — the NAT Gateway can be deleted entirely. |
| Cost Explorer shows NAT Gateway cost but Flow Logs show 0 bytes | Flow Logs are misconfigured or querying the wrong ENI. Trust Cost Explorer for the dollar amount; flag the traffic breakdown as unavailable. |

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-vpc-endpoint`, `delete-nat-gateway`, `replace-route`,
  `release-address`, `run-instances` for NAT Instance), emit:
  `CONFIRM: About to <action> on VPC <vpc-id> in region <region>. This
  affects <consequence>. Proceed? (yes/no)`. Do NOT execute until the
  operator confirms. Do NOT batch VPC changes.
- **Route-table backup before topology changes.** `aws ec2
  describe-route-tables --route-table-ids <rtb-id> --output json >
  /tmp/<rtb-id>-backup-$(date +%s).json`. Route changes are atomic and
  non-versioned.
- **Verify NAT Gateway state before relying on it.** Ensure the
  remaining NAT Gateway is `available` before deleting others.
- **Endpoint policy and private DNS review.** Default Gateway endpoint
  policy is "full access"; `--private-dns-enabled` on Interface endpoints
  overrides public DNS within the VPC. Verify no conflicts before creating.
