# NAT Gateway Pricing and Endpoint Matrix Reference

Supplementary reference for the NAT Gateway Traffic Optimizer skill.
Loaded on-demand when detailed pricing math, endpoint break-even
analysis, VPC Flow Logs query patterns, or cross-AZ cost modelling
are needed.

## NAT Gateway pricing model (us-east-1, 2026, USD)

### Per-component breakdown

| Component | Rate | Monthly (730h) | Notes |
|---|---|---|---|
| Hourly charge (base) | $0.045/hour | $32.85/month per gateway | Billed regardless of traffic volume |
| Data processing (per-GB) | $0.045/GB | varies | Billed on total bytes processed through the gateway |

### Total cost formula

```
monthly_nat_cost = (nat_gateway_count × $0.045 × 730) + (total_GB × $0.045)

Example: 2 NAT Gateways, 450 GB/month
  hourly: 2 × $0.045 × 730 = $65.70
  data processing: 450 × $0.045 = $20.25
  total: $85.95/month
```

### Elastic IP charge (attached to NAT Gateway)

| State | Charge |
|---|---|
| EIP attached to an active NAT Gateway | $0.00 (included in NAT Gateway hourly) |
| EIP attached to a deleted NAT Gateway | $0.005/hour ($3.65/month) — UNRELEASED |
| EIP not associated with any instance/gateway | $0.005/hour ($3.65/month) |

**Always release the EIP after deleting a NAT Gateway.**

## VPC Endpoint pricing comparison

### Gateway Endpoints (S3, DynamoDB) — FREE

| Component | Rate | Notes |
|---|---|---|
| Hourly charge | $0.00/hour | Free |
| Per-GB data processing | $0.00/GB | Free |
| Per-AZ charge | $0.00/AZ | Free |
| Setup cost | $0.00 | AWS-managed route table entry |

Gateway Endpoints add a prefix list (`pl-xxxxxxxx`) route to the
specified route tables. Traffic matching the prefix list is routed
through the endpoint instead of the NAT Gateway. No additional
charges apply.

### Interface Endpoints (PrivateLink) — per-AZ hourly

| Component | Rate | Monthly per AZ | Notes |
|---|---|---|---|
| Hourly charge | $0.010/hour per AZ | $7.30/AZ/month | Billed per AZ where the endpoint is deployed |
| Per-GB data processing | $0.010/GB | varies | Data processed through the endpoint |
| Setup cost | $0.00 | AWS-managed ENI |

**Interface Endpoint cost by AZ count:**
| AZs | Hourly | Monthly | Break-even GB ($7.30/$0.045 per AZ) |
|---|---|---|---|
| 1 | $0.010 | $7.30 | 162 GB/AZ |
| 2 | $0.020 | $14.60 | 324 GB total (162/AZ) |
| 3 | $0.030 | $21.90 | 486 GB total (162/AZ) |

### Gateway Load Balancer Endpoints

| Component | Rate | Notes |
|---|---|---|
| Hourly charge | $0.010/hour per AZ | Same as Interface Endpoints |
| Per-GB data processing | $0.010/GB | Traffic inspected by the GWLB |

Used for security appliance insertion (firewalls, IDS/IPS). Not
directly a NAT optimization, but relevant when NAT traffic must be
inspected.

## Break-even analysis by AWS service

### How to compute break-even

```
break_even_GB = endpoint_monthly_cost / NAT_per_GB_rate

For a 3-AZ Interface Endpoint:
  endpoint_monthly_cost = 3 × $0.010 × 730 = $21.90
  break_even = $21.90 / $0.045 = 486 GB/month (162 GB/AZ)

If service traffic > 486 GB/month → create Interface Endpoint (saves $)
If service traffic < 486 GB/month → NAT is cheaper (do NOT create)
```

### Per-service typical traffic and break-even likelihood

| Service | Endpoint type | Typical monthly traffic source | Break-even likelihood |
|---|---|---|---|
| S3 | Gateway (FREE) | S3 object reads/writes from private subnets | ALWAYS create (free) |
| DynamoDB | Gateway (FREE) | DynamoDB queries from private subnets | ALWAYS create (free) |
| ECR (api + dkr) | Interface ($21.90/3-AZ) | Docker image pulls/pushes | HIGH if CI/CD in-VPC |
| SSM | Interface ($21.90/3-AZ) | SSM Agent heartbeat, commands | HIGH if SSM-managed fleet |
| STS | Interface ($21.90/3-AZ) | AssumeRole calls from private subnets | MEDIUM |
| SQS | Interface ($21.90/3-AZ) | Queue operations from private subnets | MEDIUM-HIGH |
| Secrets Manager | Interface ($21.90/3-AZ) | Secret retrieval | MEDIUM |
| CloudWatch Logs | Interface ($21.90/3-AZ) | Log ingestion from private subnets | HIGH for logging-heavy |
| KMS | Interface ($21.90/3-AZ) | Encrypt/Decrypt API calls | LOW (small payloads) |
| CloudFormation | Interface ($21.90/3-AZ) | IaC API calls from private subnets | LOW |
| API Gateway (execute-api) | Interface ($21.90/3-AZ) | Private API calls | MEDIUM-HIGH |

### ECR break-even example

```
ECR traffic: 300 GB/month (Docker image pulls)
3-AZ Interface Endpoint cost: $21.90/month
NAT data processing eliminated: 300 × $0.045 = $13.50/month

Break-even check: $21.90 > $13.50 → Interface Endpoint LOSES $8.40/month
Verdict: Do NOT create ECR Interface Endpoint (below break-even)

But if ECR traffic is 600 GB/month:
  NAT processing eliminated: 600 × $0.045 = $27.00/month
  Endpoint cost: $21.90/month
  Net saving: $5.10/month → CREATE the Interface Endpoint
```

## Cross-AZ data transfer costs

### When cross-AZ charges apply

| Traffic path | Cost | Direction |
|---|---|---|
| EC2 in AZ-1 → NAT Gateway in AZ-1 | $0.00 (same AZ) | N/A |
| EC2 in AZ-1 → NAT Gateway in AZ-2 | $0.01/GB | Each direction |
| EC2 in AZ-2 → NAT Gateway in AZ-1 | $0.01/GB | Each direction |
| Round-trip cross-AZ via NAT | $0.02/GB total | Both directions |

### Cross-AZ impact on single-NAT consolidation

```
Scenario: 3-AZ VPC, 500 GB/month total NAT traffic
Before consolidation: 3 NAT Gateways (one per AZ), no cross-AZ
  Hourly: 3 × $32.85 = $98.55/month
  Data processing: 500 × $0.045 = $22.50/month
  Cross-AZ: $0.00 (each AZ has its own NAT)
  Total: $121.05/month

After consolidation: 1 NAT Gateway in AZ-1
  Hourly: 1 × $32.85 = $32.85/month
  Data processing: 500 × $0.045 = $22.50/month
  Cross-AZ: ~330 GB (from AZ-2 and AZ-3) × $0.01 × 2 = $6.60/month
  Total: $61.95/month
  Saving: $59.10/month (49%)

Cross-AZ added $6.60/month but saved $65.70 in hourly charges.
Net saving is still strongly positive.
```

## NAT Instance cost comparison

### NAT Instance pricing (t3.micro, us-east-1)

| Component | Rate | Monthly |
|---|---|---|
| t3.micro On-Demand | $0.0104/hour | $7.59/month |
| Data transfer IN to NAT Instance | $0.00 | Free (same AZ) |
| Data transfer OUT from NAT Instance to Internet | $0.09/GB (first 10 TB) | Varies |
| Cross-AZ transfer (if applicable) | $0.01/GB each direction | Varies |

**Important:** NAT Instance pays standard EC2 data transfer rates for
OUTBOUND traffic. The first 100 GB/month is free, then $0.09/GB for
the next 9.9 TB. This makes NAT Instances cheaper than NAT Gateways
for low traffic (< 50 GB/month outbound) but more expensive for high
traffic (> 300 GB/month outbound).

### Cost comparison at various traffic levels

| Monthly traffic | NAT Gateway | NAT Instance (t3.micro) | Winner |
|---|---|---|---|
| 10 GB | $32.85 + $0.45 = $33.30 | $7.59 + $0.00 = $7.59 | NAT Instance |
| 50 GB | $32.85 + $2.25 = $35.10 | $7.59 + $0.00 = $7.59 | NAT Instance |
| 100 GB | $32.85 + $4.50 = $37.35 | $7.59 + $0.00 = $7.59 | NAT Instance |
| 200 GB | $32.85 + $9.00 = $41.85 | $7.59 + $9.00 = $16.59 | NAT Instance |
| 500 GB | $32.85 + $22.50 = $55.35 | $7.59 + $36.00 = $43.59 | NAT Instance |
| 1,000 GB | $32.85 + $45.00 = $77.85 | $7.59 + $81.00 = $88.59 | NAT Gateway |
| 5,000 GB | $32.85 + $225.00 = $257.85 | $7.59 + $441.00 = $448.59 | NAT Gateway |

**Crossover point:** ~800 GB/month. Below 800 GB, NAT Instance is
cheaper. Above 800 GB, NAT Gateway is cheaper.

### NAT Instance limitations

| Factor | NAT Gateway | NAT Instance (t3.micro) |
|---|---|---|
| Throughput | Up to 100 Gbps | ~1 Gbps |
| Availability | Managed HA (multi-AZ capable) | Single instance, single AZ |
| Port allocation | 55,000 per eni (scalable) | Ephemeral port range (limited) |
| Scaling | Automatic | Manual (requires ASG + failover scripting) |
| SLA | 99.99% | None (EC2 SLA only) |
| Maintenance | AWS-managed | OS patches, security updates |
| Monitoring | CloudWatch built-in | Custom CloudWatch + scripts |

## VPC Flow Logs query patterns

### Query to break down NAT traffic by destination service

```
fields @timestamp, srcaddr, dstaddr, port, protocol, bytes, pktSrcAddr, pktDstAddr
| filter interfaceId = 'eni-0natGatewayENI'
| stats sum(bytes) as totalBytes by dstaddr
| sort totalBytes desc
| limit 20
```

Replace `eni-0natGatewayENI` with the NAT Gateway's ENI ID (from
`describe-nat-gateways --query 'NatGateways[0].NatGatewayAddresses[0].NetworkInterfaceId'`).

### Query to identify S3 traffic through NAT

```
fields @timestamp, srcaddr, dstaddr, bytes
| filter (dstaddr like '52.219.%' or dstaddr like '3.5.%' or dstaddr like '16.182.%')
  and bytes > 0
| stats sum(bytes) as s3Bytes by bin(1h)
| sort @timestamp asc
```

S3 IP ranges vary by region. Use the AWS IP range JSON for accurate
filtering:
`https://ip-ranges.amazonaws.com/ip-ranges.json` filtered by
`service: S3` and `region: us-east-1`.

### Query to identify ECR traffic through NAT

```
fields @timestamp, srcaddr, dstaddr, bytes
| filter (dstaddr like 'api.ecr.%' or dstaddr like 'dkr.ecr.%')
| stats sum(bytes) as ecrBytes by bin(1d)
```

### Query to quantify cross-AZ transfer

```
fields @timestamp, srcaddr, dstaddr, bytes
| filter pktSrcAcpid != pktDstAcpid  -- different AZ
| stats sum(bytes) as crossAzBytes by bin(1h)
| sort @timestamp asc
```

## CloudWatch NAT Gateway metrics reference

| Metric | Description | Unit | Use |
|---|---|---|---|
| `BytesOutToDestination` | Bytes sent from NAT to the internet | Bytes | Primary outbound traffic metric |
| `BytesInFromDestination` | Bytes received from the internet by NAT | Bytes | Primary inbound traffic metric |
| `BytesOutToSource` | Bytes sent from NAT back to the VPC | Bytes | Return traffic to private subnets |
| `BytesInFromSource` | Bytes received by NAT from the VPC | Bytes | Traffic from private subnets to NAT |
| `ConnectionEstablishedCount` | New connections established | Count | Connection rate |
| `ErrorPortAllocation` | Port allocation failures | Count | Port exhaustion indicator |
| `PacketsDropCount` | Dropped packets | Count | Dropped traffic |

### Key metric combinations

```
Total data processed = BytesInFromSource + BytesOutToDestination
  (This is the basis for the $0.045/GB charge)

Port exhaustion indicator = ErrorPortAllocation > 0
  (Indicates the NAT Gateway is running out of ephemeral ports)

Effective outbound = BytesOutToDestination
  (Traffic leaving NAT to the internet)
```

## Regional pricing multipliers

Approximate multiplier vs us-east-1 for NAT Gateway rates.

| Region | Hourly multiplier | Per-GB multiplier | Notes |
|---|---|---|---|
| us-east-1, us-east-2, us-west-2 | 1.00x | 1.00x | Baseline |
| us-west-1 | 1.05x | 1.05x | Slight premium |
| eu-west-1, eu-west-2, eu-central-1 | 1.10-1.15x | 1.10-1.15x | EU premium |
| ap-southeast-1, ap-southeast-2 | 1.12-1.18x | 1.12-1.18x | APAC premium |
| ap-northeast-1 (Tokyo) | 1.10-1.15x | 1.10-1.15x | |
| ap-south-1 (Mumbai) | 1.15-1.25x | 1.15-1.25x | |
| sa-east-1 (São Paulo) | 1.35-1.50x | 1.35-1.50x | Highest premium |

## Cost calculation worked examples

### Example 1: S3 Gateway Endpoint creation (FREE saving)

```
VPC: vpc-0prod01
Current NAT Gateways: 2 (multi-AZ production)
Current monthly traffic: 800 GB total
  S3 traffic: 300 GB (37.5%)
  Other traffic: 500 GB

Before optimization:
  Hourly: 2 × $0.045 × 730 = $65.70
  Data processing: 800 × $0.045 = $36.00
  Total: $101.70/month

After S3 Gateway Endpoint:
  S3 traffic eliminated from NAT: 300 GB
  Remaining NAT traffic: 500 GB
  Hourly: 2 × $0.045 × 730 = $65.70 (unchanged — still need multi-AZ)
  Data processing: 500 × $0.045 = $22.50
  Gateway Endpoint cost: $0.00 (free)
  Total: $88.20/month

Monthly saving: $101.70 - $88.20 = $13.50 (13%)
Annual saving: $162.00
```

### Example 2: Non-prod multi-AZ consolidation

```
VPC: vpc-0staging01 (staging, not production)
Current NAT Gateways: 3 (one per AZ)
Current monthly traffic: 200 GB total

Before optimization:
  Hourly: 3 × $0.045 × 730 = $98.55
  Data processing: 200 × $0.045 = $9.00
  Total: $107.55/month

After consolidation (1 NAT Gateway in AZ-1):
  Hourly: 1 × $0.045 × 730 = $32.85
  Data processing: 200 × $0.045 = $9.00
  Cross-AZ: ~130 GB × $0.01 × 2 = $2.60
  Total: $44.45/month

Monthly saving: $107.55 - $44.45 = $63.10 (59%)
Annual saving: $757.20

Note: After deleting 2 NAT Gateways, release 2 EIPs:
  Saving from EIP release: 2 × $0.005 × 730 = $7.30/month (additional)
  Total with EIP release: $70.40/month saving
```

### Example 3: Interface Endpoint (ECR) break-even

```
VPC: vpc-0ci01 (CI/CD VPC)
Current NAT Gateways: 1 (single AZ)
ECR traffic through NAT: 400 GB/month

Option A: Keep NAT for ECR traffic
  NAT data processing for ECR: 400 × $0.045 = $18.00/month

Option B: Create ECR Interface Endpoint (1 AZ)
  Interface Endpoint cost: $0.010 × 730 = $7.30/month
  ECR data processing through endpoint: 400 × $0.010 = $4.00/month
  Total endpoint cost: $11.30/month

Comparison:
  NAT: $18.00/month for ECR traffic
  Interface Endpoint: $11.30/month
  Saving: $6.70/month → CREATE the Interface Endpoint

Break-even: $7.30 / $0.045 = 162 GB/month
  ECR traffic (400 GB) > 162 GB → above break-even → CREATE
```

### Example 4: NAT Instance substitution (dev/test)

```
VPC: vpc-0dev01 (dev environment)
Current NAT Gateway: 1
Current monthly traffic: 30 GB

Before optimization:
  NAT Gateway: $32.85 + (30 × $0.045) = $32.85 + $1.35 = $34.20/month

After NAT Instance substitution (t3.micro):
  EC2: $0.0104 × 730 = $7.59/month
  Data transfer out: first 100 GB free → $0.00
  Total: $7.59/month

Monthly saving: $34.20 - $7.59 = $26.61 (78%)
Annual saving: $319.32

Plus EIP release: $3.65/month additional saving
Total: $30.26/month saving

Note: Dev environment only. No HA requirement. Throughput of
~1 Gbps is sufficient for dev workloads.
```

### Example 5: Combined optimization (Gateway + Interface + topology)

```
VPC: vpc-0prod01 (3-AZ production)
Current NAT Gateways: 3
Current monthly traffic: 2,000 GB total
  S3: 800 GB
  DynamoDB: 200 GB
  ECR: 400 GB
  Other: 600 GB

Before optimization:
  Hourly: 3 × $0.045 × 730 = $98.55
  Data processing: 2,000 × $0.045 = $90.00
  Total: $188.55/month

Step 1: S3 Gateway Endpoint (FREE) — eliminates 800 GB
Step 2: DynamoDB Gateway Endpoint (FREE) — eliminates 200 GB
Step 3: ECR Interface Endpoints (api + dkr, 3-AZ) — eliminates 400 GB
  Cost: 2 endpoints × 3 AZs × $0.010 × 730 = $43.80/month
  But ECR per-GB through endpoint: 400 × $0.010 = $4.00/month
  Total ECR endpoint: $47.80/month
  Saving from eliminating ECR from NAT: 400 × $0.045 = $18.00/month
  Net: $18.00 - $47.80 = -$29.80 (LOSES money! Below break-even)
  Decision: Do NOT create ECR Interface Endpoints (below break-even)

After Steps 1+2 only (Gateway Endpoints):
  Remaining traffic: 2,000 - 800 - 200 = 1,000 GB
  Hourly: 3 × $0.045 × 730 = $98.55 (keep multi-AZ for production)
  Data processing: 1,000 × $0.045 = $45.00
  Gateway Endpoints: $0.00
  Total: $143.55/month

Monthly saving: $188.55 - $143.55 = $45.00 (24%)
Annual saving: $540.00
```

## Gateway Endpoint route table verification

After creating a Gateway Endpoint, verify the route was added:

```bash
# Check route tables for the prefix list route
aws ec2 describe-route-tables \
  --filters Name=vpc-id,Values=vpc-0abc123 \
  --query 'RouteTables[].{RTB:RouteTableId,Routes:Routes[?GatewayId!=null]}' \
  --output json

# The Gateway Endpoint creates a route like:
# { "DestinationPrefixListId": "pl-68a54001", "GatewayId": "vpce-0xxx" }
```

If the route is missing from a subnet's route table (e.g., when using
custom route tables per subnet), add it manually:

```bash
aws ec2 create-route --route-table-id rtb-0xxx \
  --destination-prefix-list-id pl-68a54001 \
  --vpc-endpoint-id vpce-0xxx
```

## Interface Endpoint security group

Interface Endpoints require a security group that allows inbound HTTPS
(443) from the VPC CIDR. Create a dedicated security group:

```bash
aws ec2 create-security-group \
  --group-name vpc-endpoint-sg \
  --description "Allow HTTPS for VPC Endpoints" \
  --vpc-id vpc-0abc123

aws ec2 authorize-security-group-ingress \
  --group-id sg-0endpoint \
  --protocol tcp --port 443 \
  --cidr 10.0.0.0/16
```
