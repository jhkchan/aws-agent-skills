# Diagnostic Commands (load on demand) — Data Transfer Optimizer

Pre-flight data-gate sources, per-step CLI listings (Cost Explorer, NAT
Gateway, CloudWatch flow-log analysis), the 60-second triage, and pre-flight
safety checks moved verbatim from SKILL.md. Loaded on demand.

---

## Pre-flight: data gate — required data sources (intro) (moved from SKILL.md)



Data transfer optimization requires three data sources: Cost
Explorer / CUR for billing, VPC topology for routing decisions, and
service-level configurations (RDS, S3, NAT Gateway) for per-resource
context.



## Pre-flight: data gate — required data sources (moved from SKILL.md)



```bash
# 1. Pull Cost Explorer data-transfer line items (last 30 days)
START=$(date -u -d '-30 days' +%F)
END=$(date -u +%F)

aws ce get-cost-and-usage \
  --time-period Start=$START,End=$END \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":[
    "Amazon Elastic Compute Cloud - Compute",
    "AmazonEC2",
    "Amazon Simple Storage Service",
    "Amazon Relational Database Service",
    "Amazon ElastiCache",
    "Amazon Redshift",
    "Amazon DynamoDB",
    "Amazon Nat Gateway",
    "Amazon Virtual Private Cloud",
    "Amazon Route 53",
    "AWS Direct Connect"
  ]}}' \
  --granularity MONTHLY \
  --metrics "BlendedCost" "UsageQuantity" \
  --group-by Type=DIMENSION,Key=USAGE_TYPE \
  --output json > ce-data-transfer.json

# 2. Pull VPC topology
aws ec2 describe-nat-gateways --output json > nat-gateways.json
aws ec2 describe-vpc-peering-connections --output json > vpc-peerings.json
aws ec2 describe-transit-gateways --output json > transit-gateways.json
aws ec2 describe-vpc-endpoints --output json > vpc-endpoints.json

# 3. Pull service configurations (top-cost resources)
aws rds describe-db-instances --output json > rds-instances.json
aws s3api list-buckets --output json | \
  jq '[.Buckets[] | {name, region: "us-east-1"}]' > s3-buckets.json
# For each bucket, get actual region:
for bucket in $(jq -r '.[].name' s3-buckets.json); do
  region=$(aws s3api get-bucket-location --bucket $bucket \
    --query 'LocationConstraint' --output text)
  echo "$bucket,$region"
done > bucket-regions.csv

# 4. Pull Direct Connect (if in use)
aws directconnect describe-connections --output json > dx-connections.json
```



## Step 2 — Cost Explorer reconciliation CLI and USAGE_TYPE mapping (moved from SKILL.md)



```bash
aws ce get-cost-and-usage \
  --time-period Start=$(date -u -d '-30 days' +%F),End=$(date -u +%F) \
  --granularity MONTHLY \
  --metrics "BlendedCost" "UsageQuantity" \
  --group-by Type=DIMENSION,Key=USAGE_TYPE \
  --filter '{"Dimensions":{"Key":"USAGE_TYPE_GROUP","Values":[
    "EC2: Data Transfer - Internet (Out)",
    "EC2: Data Transfer - Region (Out)",
    "EC2: Data Transfer - Availability Zone (Out)",
    "EC2: Egress - Cross Region",
    "S3: Cross-Region Replication",
    "CloudFront: Egress",
    "RDS: Data Transfer",
    "VPC: NAT Gateway",
    "VPC: Transit Gateway"
  ]}}' \
  --output json | \
  jq '.ResultsByTime[].Groups[] | {usage: .Keys[0],
    cost: (.Metrics.BlendedCost.Amount | tonumber),
    usage_qty: (.Metrics.UsageQuantity.Amount | tonumber)}'
```

| USAGE_TYPE | Dimension | What it represents |
|---|---|---|
| `NatGateway-Bytes` | NAT Gateway | $0.045/GB processed |
| `DataTransfer-Regional-Bytes` | Cross-AZ | $0.01/GB each direction |
| `DataTransfer-Out-Bytes` | Internet egress | $0.09/GB first 10TB |
| `DataTransfer-Egress-Cross-Region` | Cross-region | $0.02-0.09/GB by region pair |
| `S3-Cross-Region-Replication-Bytes` | S3 CRR | Cross-region transfer + S3 requests |
| `RDS-DataTransfer` | RDS Multi-AZ | $0.01/GB for non-Aurora Multi-AZ |
| `TransitGateway-Bytes` | TGW | $0.02/GB inbound + outbound |

If a single USAGE_TYPE accounts for > 50% of the total data-transfer
cost, deep-dive that dimension first. The Pareto principle applies
heavily — typically NAT Gateway or internet egress dominates.



## Step 4 — detecting cross-AZ waste via CloudWatch and Athena (moved from SKILL.md)



**Detecting cross-AZ waste via CloudWatch:**

```bash
# For each EC2 instance, get network throughput by peer-AZ
# (Requires VPC Flow Logs enabled)
aws ec2 describe-flow-logs --output json

# Athena query on VPC Flow Logs to identify cross-AZ traffic
SELECT
  concat(split_part(srcaddr, '.', 1), '.',
         split_part(srcaddr, '.', 2), '.x.x') AS src_subnet,
  concat(split_part(dstaddr, '.', 1), '.',
         split_part(dstaddr, '.', 2), '.x.x') AS dst_subnet,
  SUM(bytes) AS total_bytes
FROM vpc_flow_logs
WHERE date >= date_add('day', -7, now())
  AND action = 'ACCEPT'
GROUP BY 1, 2
ORDER BY 3 DESC LIMIT 20;
```



## Step 5 — NAT Gateway inventory and throughput CLI (moved from SKILL.md)



```bash
# Identify NAT Gateways and their throughput
aws ec2 describe-nat-gateways --output json | \
  jq '.NatGateways[] | {id: .NatGatewayId, state: .State,
    az: .SubnetId, public_ip: .NatGatewayAddresses[0].PublicIp}'

# Get NAT Gateway traffic (CloudWatch)
for nat in $(aws ec2 describe-nat-gateways --query 'NatGateways[].NatGatewayId' --output text); do
  aws cloudwatch get-metric-statistics \
    --namespace AWS/NATGateway \
    --metric-name BytesOutToDestination \
    --dimensions Name=NatGatewayId,Value=$nat \
    --start-time $(date -u -d '-30 days' +%FT%TZ) \
    --end-time $(date -u +%FT%TZ) \
    --period 86400 --statistics Sum \
    --output json
done
```



## Expert heuristic — the 60-second triage (moved from SKILL.md)



When handed a data-transfer bill and asked "why is this so high?",
run this 60-second triage before deep-diving any single dimension:

1. **Pull CE data-transfer breakdown.** If NAT Gateway is > 30% of
   the bill, deep-dive Step 5 (Gateway Endpoints).
2. **Pull VPC endpoint inventory.** No Gateway Endpoints in VPCs
   with private subnets = guaranteed optimization.
3. **Pull NAT Gateway count.** > 1 NAT per VPC + low traffic =
   consider consolidating (dev/test) or accepting HA cost (prod).
4. **Pull VPC topology.** > 4 VPCs on Transit Gateway with low
   inter-VPC traffic = peering migration candidate.
5. **Pull RDS Multi-AZ status.** Non-Aurora Multi-AZ on high-write
   workload = Aurora migration candidate.
6. **Pull internet egress volume.** > 10TB/month to global viewers
   without CloudFront = CloudFront migration candidate.

If any of the six checks hits, deep-dive the corresponding step.
If all six pass, the account is likely ALREADY_OPTIMAL on data
transfer — verify with the full ordered process.



## Pre-flight safety checks (run before any remediation CLI) (moved from SKILL.md)



- **MANDATORY CONFIRMATION GATE.** Before any state-changing
  operation (`create-vpc-endpoint`, `modify-route-table`,
  `delete-nat-gateway`, `create-vpc-peering-connection`,
  `delete-transit-gateway-vpc-attachment`), emit and await operator
  approval.

- **Snapshot route tables before any change.** Capture the current
  state:
  ```bash
  for rtb in $(aws ec2 describe-route-tables --query 'RouteTables[].RouteTableId' --output text); do
    aws ec2 describe-route-tables --route-table-ids $rtb --output json \
      > rtb-backup-$rtb-$(date +%s).json
  done
  ```
  This provides a rollback path if a route change breaks connectivity.

- **One dimension per maintenance window.** Route changes, ASG
  changes, and Gateway Endpoint deployments each affect network
  behavior; stacking them obscures which change produced any
  observed impact.

- **Verify Gateway Endpoint propagation.** After creating a Gateway
  Endpoint, confirm the route table has the new prefix list entry:
  ```bash
  aws ec2 describe-route-tables --route-table-ids <rtb> --output json | \
    jq '.RouteTables[].Routes[] | select(.DestinationPrefixListId != null)'
  ```

- **Verify NAT Gateway removal is safe.** Before deleting a NAT,
  confirm no security groups or route tables still reference it:
  ```bash
  aws ec2 describe-route-tables --output json | \
    jq '.RouteTables[] | select(.Routes[].NatGatewayId != null)'
  ```

- **Bulk-operation safety limit.** Optimization across a fleet of
  VPCs MUST follow this algorithm:
  1. Sort flagged VPCs by estimated savings (largest first).
  2. Slice into batches of at most 3 VPCs.
  3. For each batch: emit per-VPC MIGRATION_STEPS, then a single
     CONFIRM for the batch.
  4. After the operator confirms and the CLI runs, re-query with
     `describe-route-tables` and verify connectivity before
     emitting the NEXT batch.
  5. Abort the sweep if any VPC loses connectivity or shows
     elevated error rates.
  The skill MUST NOT emit remediation CLI for more than 3 VPCs in
  a single output block.

- **RDS failover safety.** If an AZ-pinning change requires moving
  the primary DB, use `aws rds reboot-db-instance --force-failover`
  during a maintenance window. Do NOT trigger failover outside
  maintenance windows.

- **Direct Connect commit is billing-account-level.** A DX port is
  a physical connection at a colocation facility; committing to
  a 1Gbps port for 12 months affects the entire payer account.
  Surface this in the CONFIRMATION gate.


