# AWS Data Transfer Pricing & Decision Reference

Supplementary reference for the Data Transfer Optimizer skill. Loaded
on-demand when the optimizer needs the detailed pricing matrix, NAT
Gateway break-even math, VPC peering vs Transit Gateway crossover, or
Direct Connect sizing logic.

## Cross-AZ data transfer pricing

Every GB crossing an AZ boundary within the same region pays $0.01
in each direction. Round-trip cost is $0.02/GB.

### Same-AZ (free) vs cross-AZ ($0.02) decision matrix

| Source → Destination | Same-AZ cost | Cross-AZ cost |
|---|---|---|
| EC2 → EC2 (private IP) | FREE | $0.01/GB each way |
| EC2 → RDS primary | FREE | $0.01/GB each way |
| EC2 → ElastiCache primary | FREE | $0.01/GB each way |
| EC2 → ALB | FREE | $0.01/GB each way |
| EC2 → EFS (mount target in same AZ) | FREE | $0.01/GB to mount target in another AZ |
| EC2 → S3 (via Gateway Endpoint) | FREE (regional) | FREE (regional — S3 is not AZ-specific) |
| RDS Multi-AZ replication (non-Aurora) | n/a | $0.01/GB |
| Aurora Multi-AZ replication | n/a | FREE (storage-layer replication) |

### AZ-pinning worked example

3-tier app: EC2 web servers in 3 AZs, RDS primary in us-east-1a,
RDS standby in us-east-1b. Web servers read 200GB/day from primary.

- Current cross-AZ traffic: 2/3 of web servers are cross-AZ →
  133GB/day cross-AZ × $0.02/GB × 30 = $80/month
- Pin web servers to us-east-1a: $0/month (same-AZ traffic is free)
- Trade-off: web layer loses multi-AZ HA. Mitigate with standby ASG
  in us-east-1b (min=0, scale on primary AZ health alarm).

## Cross-region data transfer pricing (per GB, outbound)

Cross-region pricing depends on the source/destination region pair.
Regions within the same continent are cheaper than intercontinental.

### North America → other regions

| Source → Destination | Rate |
|---|---|
| us-east-1 → us-west-2 | $0.02/GB |
| us-east-1 → us-east-2 | $0.02/GB |
| us-east-1 → ca-central-1 | $0.02/GB |
| us-east-1 → eu-west-1 | $0.02/GB |
| us-east-1 → eu-central-1 | $0.02/GB |
| us-east-1 → ap-northeast-1 (Tokyo) | $0.09/GB |
| us-east-1 → ap-southeast-1 (Singapore) | $0.09/GB |
| us-east-1 → ap-south-1 (Mumbai) | $0.09/GB |
| us-east-1 → sa-east-1 (São Paulo) | $0.16/GB |
| us-east-1 → af-south-1 (Cape Town) | $0.16/GB |
| us-east-1 → me-south-1 (Bahrain) | $0.09/GB |
| us-east-1 → ap-east-1 (Hong Kong) | $0.09/GB |
| us-east-1 → CloudFront | FREE from S3; $0.02/GB from EC2 |
| us-east-1 → Direct Connect | $0.02/GB |

### Intercontinental rate patterns

| Region pair pattern | Typical rate |
|---|---|
| Within North America | $0.02/GB |
| Within Europe | $0.02/GB |
| Within Asia Pacific | $0.02-0.09/GB |
| North America ↔ Europe | $0.02/GB |
| North America ↔ Asia Pacific | $0.09/GB |
| North America ↔ South America | $0.16/GB |
| Europe ↔ Asia Pacific | $0.09/GB |
| Any region → Africa | $0.16/GB |

### Cross-region architecture patterns

| Pattern | Use case | Cost |
|---|---|---|
| Cross-region VPC peering | Direct VPC-to-VPC traffic | $0.01-0.02/GB (per-region-pair) |
| Transit Gateway cross-region attachment | Hub-and-spoke cross-region | $0.02/GB in + $0.02/GB out |
| VPC peering + DX gateway | Hybrid on-prem + multi-region | DX per-GB + peering per-GB |
| S3 Cross-Region Replication | DR for S3 objects | Cross-region transfer + S3 PUT requests |
| Aurora Global Database | DR for Aurora | Aurora storage pricing (no per-GB cross-region transfer) |
| DynamoDB Global Tables | Multi-region active-active | Cross-region replication per-GB |

## Internet egress pricing (tiered)

| Monthly volume | Rate |
|---|---|
| First 10 TB | $0.09/GB |
| Next 40 TB (10-50 TB) | $0.085/GB |
| Next 100 TB (50-150 TB) | $0.070/GB |
| Next 350 TB (150-500 TB) | $0.050/GB |
| Above 500 TB | Contact AWS |

### Worked egress optimization examples

**Example 1: S3 egress to global viewers (5TB/month)**

- Direct from S3: 5,000GB × $0.09 = $450/month
- Via CloudFront (PriceClass_100): 5,000GB × $0.085 = $425/month
  (CF-to-viewer) + $0 S3-to-CF + ~$1 in request charges = ~$426/month
- Savings: $24/month on egress alone; plus cache-hit savings if
  CacheHitRate > 90%.

**Example 2: EC2 egress to global viewers (20TB/month)**

- Direct from EC2: tiered internet egress = 10TB × $0.09 + 10TB ×
  $0.085 = $900 + $850 = $1,750/month
- Via CloudFront: 20TB × $0.085 (CF-to-viewer) + 20TB × $0.02
  (EC2-to-CF same-region) = $1,700 + $400 = $2,100/month
- Direct is cheaper — CloudFront adds $0.02/GB origin-to-CF on top
  of CF-to-viewer. CloudFront wins only when cache-hit savings or
  APAC-tier avoidance outweighs the origin-to-CF cost.

**Example 3: On-prem sync (50TB/month steady)**

- Internet egress: 10TB × $0.09 + 40TB × $0.085 + 10TB × $0.07
  (50-150TB tier) ≈ $900 + $3,400 + $700 = $5,000/month (rough)
  Actually, let me recompute: 50TB total. 10TB × $0.09 + 40TB ×
  $0.085 = $900 + $3,400 = $4,300/month
- Direct Connect 10Gbps: $2,000/month port + 50TB × $0.02/GB =
  $2,000 + $1,000 = $3,000/month
- DX savings: $1,300/month + committed bandwidth (vs best-effort
  internet)

## NAT Gateway pricing and break-even

### Cost components

| Component | Rate |
|---|---|
| Per GB processed (in either direction) | $0.045/GB |
| Hourly per NAT Gateway | $0.045/hour |

### Per-architecture monthly cost

| Architecture | Hourly base | Per-GB cost on 10TB traffic |
|---|---|---|
| 1 NAT Gateway (single AZ) | $32.85/month | $450 |
| 3 NAT Gateways (HA multi-AZ) | $98.55/month | $450 (traffic distributed) |
| 1 NAT Gateway + S3 Gateway Endpoint | $32.85/month | $0 (S3 routed free) |
| 3 NAT Gateways + S3 + DynamoDB Gateway Endpoints | $98.55/month | $0 (S3 + DynamoDB routed free) |

### Gateway Endpoint vs Interface Endpoint vs NAT

| Service | Gateway Endpoint (free) | Interface Endpoint ($0.05/AZ/h + $0.01/GB) | NAT Gateway ($0.045/h + $0.045/GB) |
|---|---|---|---|
| S3 | Yes (recommended) | Yes (for hybrid scenarios) | Default (most expensive) |
| DynamoDB | Yes (recommended) | Yes (for hybrid scenarios) | Default (most expensive) |
| SQS, SNS, Kinesis | No (Interface only) | Yes | Default (most expensive) |
| Secrets Manager, STS, etc. | No (Interface only) | Yes (low traffic, may not break even) | Default |
| Third-party APIs | No | No (PrivateLink for partners, different model) | Required |

### Interface Endpoint break-even math

```
interface_endpoint_monthly = (endpoint_count × AZ_count × $0.05 × 730)
                             + (GB × $0.01)
nat_monthly = (GB × $0.045) + (nat_count × $0.045 × 730)

# When comparing Interface Endpoint vs NAT on the same traffic:
break_even_GB = (AZ_count × $0.05 × 730) / ($0.045 - $0.01)
              = (AZ_count × 36.5) / 0.035
              ≈ 1042 × AZ_count GB/month
```

For 3 AZs: break-even ≈ 3,127 GB/month.

| Traffic volume (3-AZ) | NAT cost | Interface Endpoint cost | Winner |
|---|---|---|---|
| 1 TB/month | $45 + $32.85 = $77.85 | $10 + $109.50 = $119.50 | NAT |
| 2 TB/month | $90 + $32.85 = $122.85 | $20 + $109.50 = $129.50 | NAT (marginal) |
| 3 TB/month | $135 + $32.85 = $167.85 | $30 + $109.50 = $139.50 | Interface Endpoint |
| 5 TB/month | $225 + $32.85 = $257.85 | $50 + $109.50 = $159.50 | Interface Endpoint |
| 10 TB/month | $450 + $32.85 = $482.85 | $100 + $109.50 = $209.50 | Interface Endpoint |

Note: Above assumes 1 NAT Gateway. For HA (3 NAT Gateways), add
2 × $32.85 = $65.70 to NAT column. Interface Endpoint is even more
favored in HA scenarios.

## VPC peering vs Transit Gateway cost comparison

### Intra-region cost

| Topology | Per-GB cost | Hourly base | Notes |
|---|---|---|---|
| VPC peering (intra-region) | FREE | FREE | Per-pair only |
| Transit Gateway | $0.02/GB (in + out = $0.04 round trip) | $0.05/h per attachment | Centralized routing |

### Full-mesh connection count

| N VPCs | Peering connections (N(N-1)/2) | Operational complexity |
|---|---|---|
| 2 | 1 | Trivial |
| 3 | 3 | Manageable |
| 4 | 6 | Manageable |
| 5 | 10 | Painful without automation |
| 8 | 28 | Painful even with automation |
| 10 | 45 | Infeasible manually |
| 15 | 105 | TGW strongly preferred |

### Cost worked example: 5 VPCs, intra-region, 50GB/month per pair

- Peering: 10 connections × FREE = $0/month
- TGW: 5 attachments × $0.05/h × 730h = $182.50/month +
  10 pairs × 50GB × $0.04 (round-trip) = $20/month in per-GB =
  $202.50/month total
- Peering saves $202.50/month, but requires managing 10 connections.

### Cross-region cost

| Topology | Per-GB cost | Hourly base | Notes |
|---|---|---|---|
| Cross-region VPC peering | $0.01-0.02/GB | FREE | Region-pair-dependent rate |
| TGW cross-region attachment | $0.02/GB in + $0.02/GB out | $0.05/h per attachment | Centralized + cross-region routing |

Cross-region pricing is roughly equivalent between peering and TGW.
TGW wins on operational simplicity for hub-and-spoke or multi-region
topologies.

## Direct Connect sizing and break-even

### Port pricing (us-east-1 baseline)

| Port speed | Port monthly | Per-GB outbound |
|---|---|---|
| 50 Mbps | ~$60 | $0.02/GB |
| 100 Mbps | ~$80 | $0.02/GB |
| 200 Mbps | ~$110 | $0.02/GB |
| 300 Mbps | ~$140 | $0.02/GB |
| 400 Mbps | ~$170 | $0.02/GB |
| 500 Mbps | ~$200 | $0.02/GB |
| 1 Gbps | ~$220 | $0.02/GB |
| 2 Gbps | ~$440 | $0.02/GB |
| 5 Gbps | ~$1,100 | $0.02/GB |
| 10 Gbps | ~$2,000 | $0.02/GB |
| 100 Gbps | ~$20,000 | $0.02/GB |

### Break-even vs internet egress

```
break_even_GB = port_monthly_cost / (internet_rate - $0.02)
```

For internet at $0.09/GB (first 10TB tier):

| Port speed | Port monthly | Break-even vs $0.09/GB |
|---|---|---|
| 50 Mbps | $60 | 857 GB/month |
| 1 Gbps | $220 | 3,143 GB/month |
| 10 Gbps | $2,000 | 28,571 GB/month |
| 100 Gbps | $20,000 | 285,714 GB/month |

For higher-tier internet rates (assumes volume already in higher
tiers):

| Internet tier | Rate | 1 Gbps DX break-even |
|---|---|---|
| First 10TB | $0.09/GB | 3,143 GB/month |
| 10-50TB | $0.085/GB | 3,667 GB/month |
| 50-150TB | $0.07/GB | 6,333 GB/month |
| 150-500TB | $0.05/GB | 14,667 GB/month |

### Direct Connect use cases

| Use case | Recommended DX |
|---|---|
| Hybrid data center (< 1TB/month sync) | Internet + Site-to-Site VPN (DX overkill) |
| Hybrid data center (1-5TB/month) | 50-500 Mbps DX |
| Hybrid data center (5-50TB/month) | 1 Gbps DX |
| Hybrid data center (> 50TB/month) | 10 Gbps DX |
| Multi-region active-active with on-prem | 1+ Gbps DX per region + DX Gateway |
| Disaster recovery to on-prem | DX sized to RTO/RPO requirements |

## RDS and Aurora data transfer pricing

### RDS for MySQL/PostgreSQL (non-Aurora)

| Configuration | Data transfer charge |
|---|---|
| Single-AZ | Standard EC2 cross-AZ/region charges apply to client traffic |
| Multi-AZ (primary-standby) | $0.01/GB on synchronous replication |
| Read replica same-region | $0.01/GB cross-AZ if replica in different AZ |
| Read replica cross-region | Cross-region transfer ($0.02-0.16/GB) |

### Aurora (MySQL/PostgreSQL)

| Configuration | Data transfer charge |
|---|---|
| Single-AZ | Standard charges to client traffic |
| Multi-AZ (cluster mode) | FREE (storage-layer replication) |
| Read replica same-region | FREE (cluster volume shared) |
| Aurora Global Database | Aurora storage pricing (no per-GB cross-region transfer) |

### Worked RDS Multi-AZ vs Aurora migration

RDS for PostgreSQL db.r6i.2xlarge, Multi-AZ, 5TB write volume per
month.

- RDS Multi-AZ replication cost: 5,000GB × $0.01 = $50/month
- Aurora equivalent: $0 cross-AZ transfer (storage-layer replication)
- Net data-transfer savings: $50/month
- Aurora instance pricing: similar to RDS for same vCPU/memory
- Aurora storage pricing: $0.10/GB-month + $0.20/1M I/O requests
  (may be higher than RDS for low-I/O workloads)
- Migration effort: 1-2 weeks for app compatibility testing
- Decision: migrate if other Aurora benefits (HA, reader scale,
  auto-scaling storage) align; treat $50/month as a bonus.

## CUR USAGE_TYPE reference

| USAGE_TYPE prefix | Dimension |
|---|---|
| `USW1-AWS-Out-Bytes` | Internet egress from us-west-1 |
| `NatGateway-Bytes` | NAT Gateway data processed |
| `DataTransfer-Regional-Bytes` | Cross-AZ transfer |
| `DataTransfer-Egress-Cross-Region` | Cross-region transfer |
| `S3-Cross-Region-Replication-Bytes` | S3 CRR |
| `RDS-DataTransfer` | RDS Multi-AZ replication |
| `TransitGateway-Bytes` | TGW data processed |
| `VPC-Endpoint-Bytes` | Interface Endpoint data processed |

For USAGE_TYPE codes, see
https://docs.aws.amazon.com/cur/latest/userguide/cur-ugs.html for
the canonical reference.

## AWS documentation cross-links

- EC2 Data Transfer pricing: https://aws.amazon.com/ec2/pricing/on-demand/ (Data Transfer section)
- VPC pricing: https://aws.amazon.com/vpc/pricing/
- NAT Gateway pricing: https://aws.amazon.com/vpc/pricing/#NAT_Gateways
- VPC Endpoints pricing: https://aws.amazon.com/vpc/pricing/#Endpoints
- Transit Gateway pricing: https://aws.amazon.com/vpc/pricing/#Transit_Gateway
- Direct Connect pricing: https://aws.amazon.com/directconnect/pricing/
- S3 pricing: https://aws.amazon.com/s3/pricing/
- RDS pricing: https://aws.amazon.com/rds/pricing/
- Aurora pricing: https://aws.amazon.com/rds/aurora/pricing/
- Data Transfer Savings Plans: https://aws.amazon.com/savingsplans/data-transfer-pricing/
