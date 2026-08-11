# ELB Pricing and LCU Matrix — Reference

Supplementary reference for the ELB Cost Optimizer skill. Detailed
pricing for ALB, NLB, CLB, and Gateway Load Balancer, LCU dimension
calculations, data transfer rates, and regional notes.

## Load balancer pricing (us-east-1, 2026, USD)

### Per-hour rates

| Type | Hourly rate | Monthly (730h) | Notes |
|---|---|---|---|
| ALB | $0.0225 | $16.43 | + LCU charges |
| NLB | $0.0225 | $16.43 | + $0.006/GB processed |
| CLB | $0.025 | $18.25 | + $0.008/GB processed |
| Gateway LB | $0.0125 | $9.13 | + $0.0035/GB processed |

### ALB LCU pricing

ALB charges $0.008 per LCU-hour. The number of LCUs is determined by
the MAX of four dimensions:

| Dimension | 1 LCU = | Metric name | CloudWatch namespace |
|---|---|---|---|
| New connections | 25 new connections/sec | NewConnectionCount | AWS/ApplicationELB |
| Active connections | 3000 active connections | ActiveConnectionCount | AWS/ApplicationELB |
| Processed bytes | 1 GB/hour (2.78 Mbps) | ProcessedBytes | AWS/ApplicationELB |
| Rule evaluations | 1000 rule evaluations/sec | RuleEvaluations | AWS/ApplicationELB |

### LCU calculation examples

**Scenario A: High connection rate**

| Dimension | Value | LCUs |
|---|---|---|
| New connections | 500/sec | 500/25 = 20.0 |
| Active connections | 12,000 | 12000/3000 = 4.0 |
| Processed bytes | 1.5 GB/hr | 1.5/1 = 1.5 |
| Rule evaluations | 2,000/sec | 2000/1000 = 2.0 |
| **Billed (max)** | | **20.0 LCU** |

Cost: 20 x $0.008 x 730 = $116.80/month LCU + $16.43 base = $133.23

**Scenario B: High data transfer**

| Dimension | Value | LCUs |
|---|---|---|
| New connections | 100/sec | 100/25 = 4.0 |
| Active connections | 5,000 | 5000/3000 = 1.67 |
| Processed bytes | 15 GB/hr | 15/1 = 15.0 |
| Rule evaluations | 500/sec | 500/1000 = 0.5 |
| **Billed (max)** | | **15.0 LCU** |

Cost: 15 x $0.008 x 730 = $87.60/month LCU + $16.43 base = $104.03

**Scenario C: Low traffic (small app)**

| Dimension | Value | LCUs |
|---|---|---|
| New connections | 20/sec | 20/25 = 0.8 |
| Active connections | 800 | 800/3000 = 0.27 |
| Processed bytes | 0.2 GB/hr | 0.2/1 = 0.2 |
| Rule evaluations | 100/sec | 100/1000 = 0.1 |
| **Billed (max)** | | **0.8 LCU** |

Cost: 0.8 x $0.008 x 730 = $4.67/month LCU + $16.43 base = $21.10

## NLB pricing

NLB charges $0.0225/hour + $0.006/GB processed by the NLB. Cross-zone
load balancing (when enabled) adds $0.01/GB of cross-AZ traffic.

| NLB traffic | Monthly GB | GB charge | Cross-zone (if on) |
|---|---|---|---|
| Small | 100 GB | $0.60 | $1.00 |
| Medium | 1,000 GB (1 TB) | $6.00 | $10.00 |
| Large | 10,000 GB (10 TB) | $60.00 | $100.00 |
| Very large | 50,000 GB (50 TB) | $300.00 | $500.00 |

**NLB cross-zone cost impact:**
At 10 TB/month with cross-zone enabled, the $100 cross-zone charge
exceeds the $16.43 base NLB cost. Always evaluate whether cross-zone
is necessary.

## CLB pricing

CLB charges $0.025/hour + $0.008/GB processed.

| CLB traffic | Monthly cost (base + GB) |
|---|---|
| 100 GB | $18.25 + $0.80 = $19.05 |
| 1 TB | $18.25 + $8.00 = $26.25 |
| 5 TB | $18.25 + $40.00 = $58.25 |

## ALB vs NLB cost comparison (by workload profile)

| Workload | ALB cost | NLB cost | Winner |
|---|---|---|---|
| HTTP, 500 req/sec, 2 TB/month | $16.43 + ~$117 LCU = $133 | $16.43 + $12 + $0 cross-zone = $28 | NLB cheaper (but no HTTP features) |
| HTTP, 50 req/sec, 0.5 TB | $16.43 + ~$12 LCU = $28 | $16.43 + $3 = $19 | NLB cheaper |
| TCP, 10k connections, 5 TB, cross-zone | Not applicable | $16.43 + $30 + $50 = $96 | NLB only |
| HTTP, 200 req/sec, 1 TB, keep-alive on | $16.43 + ~$50 LCU = $66 | $16.43 + $6 = $22 | NLB cheaper (but no HTTP features) |

Note: ALB provides HTTP/HTTPS features (path routing, SNI, headers,
SSL termination) that NLB does not. The cost comparison should include
the value of features, not just the dollar cost.

## Access log S3 storage costs

| ALB traffic | Log volume/month | S3 Standard | S3 with lifecycle (IA@30d) |
|---|---|---|---|
| 1M req/day | ~30 GB | $0.69 | $0.25 |
| 10M req/day | ~300 GB | $6.90 | $2.20 |
| 100M req/day | ~3,000 GB | $69.00 | $20.00 |

Lifecycle rules (Standard-IA at 30d, Glacier at 90d, expire at 365d)
reduce effective S3 cost by 70-90%.

## Regional notes

- us-east-1, us-west-2, eu-west-1: baseline rates (shown above).
- ap-southeast-1, ap-northeast-1: ~5-10% higher per-hour rates.
- LCU rates are consistent across regions.
- Data transfer rates for cross-zone are consistent at $0.01/GB for
  NLB across all regions.
- Always re-state rates from `aws ce get-cost-and-usage` for accurate
  savings in non-us-east-1 regions.
