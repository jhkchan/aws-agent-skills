# RI and Savings Plans Pricing Matrix — Reference

Supplementary reference for the EC2 Reserved Capacity Optimizer skill.
Detailed pricing for Standard RIs, Convertible RIs, Compute Savings
Plans, and EC2 Instance Savings Plans across common instance types,
terms, and payment options.

## On-Demand baseline rates (us-east-1, Linux, 2026, USD per hour)

| Instance type | vCPU | Memory (GB) | On-Demand hourly | Monthly (730h) |
|---|---|---|---|---|
| m5.large | 2 | 8 | $0.096 | $70.08 |
| m5.xlarge | 4 | 16 | $0.192 | $140.16 |
| m5.2xlarge | 8 | 32 | $0.384 | $280.32 |
| m5.4xlarge | 16 | 64 | $0.768 | $560.64 |
| c5.large | 2 | 4 | $0.085 | $62.05 |
| c5.xlarge | 4 | 8 | $0.170 | $124.10 |
| c5.2xlarge | 8 | 16 | $0.340 | $248.20 |
| c6i.xlarge | 4 | 8 | $0.170 | $124.10 |
| c7g.xlarge (Graviton) | 4 | 8 | $0.1415 | $103.30 |
| r5.large | 2 | 16 | $0.126 | $91.98 |
| r5.xlarge | 4 | 32 | $0.252 | $183.96 |
| t3.medium | 2 | 4 | $0.0416 | $30.37 |

## Standard RI pricing (us-east-1, Linux, 2026)

### m5.large

| Term | Payment | Hourly effective | Upfront | Monthly | Discount vs OD |
|---|---|---|---|---|---|
| 1yr | No Upfront | $0.071 | $0 | $51.83 | 26% |
| 1yr | Partial Upfront | $0.063 | $167 | $19.35 | 34% |
| 1yr | All Upfront | $0.058 | $337 | $0 | 40% |
| 3yr | No Upfront | $0.053 | $0 | $38.69 | 45% |
| 3yr | Partial Upfront | $0.044 | $239 | $13.14 | 54% |
| 3yr | All Upfront | $0.038 | $278 | $0 | 60% |

### c5.xlarge

| Term | Payment | Hourly effective | Upfront | Monthly | Discount vs OD |
|---|---|---|---|---|---|
| 1yr | No Upfront | $0.126 | $0 | $91.98 | 26% |
| 1yr | All Upfront | $0.103 | $598 | $0 | 39% |
| 3yr | No Upfront | $0.094 | $0 | $68.62 | 45% |
| 3yr | All Upfront | $0.067 | $489 | $0 | 60% |

## Convertible RI pricing (us-east-1, Linux, 2026)

Convertible RIs cost ~10% less discount than Standard RIs but can be
exchanged within the same instance family and region.

### m5.large

| Term | Payment | Hourly effective | Discount vs OD |
|---|---|---|---|
| 1yr | No Upfront | $0.077 | 20% |
| 1yr | All Upfront | $0.065 | 32% |
| 3yr | No Upfront | $0.059 | 39% |
| 3yr | All Upfront | $0.045 | 53% |

## Compute Savings Plans (us-east-1, 2026)

Compute SP applies to EC2, Fargate, and Lambda. Flexible across
instance families, sizes, AZs, OS, and services.

| Term | Payment | Discount vs OD |
|---|---|---|
| 1yr | No Upfront | ~20% |
| 1yr | All Upfront | ~28% |
| 3yr | No Upfront | ~38% |
| 3yr | All Upfront | ~54% |

## EC2 Instance Savings Plans (us-east-1, 2026)

EC2 Instance SP commits to an instance family in a region. Flexible
across sizes and AZs within the family.

| Term | Payment | Discount vs OD |
|---|---|---|
| 1yr | No Upfront | ~24% |
| 1yr | All Upfront | ~32% |
| 3yr | No Upfront | ~44% |
| 3yr | All Upfront | ~72% |

## Discount comparison summary (3yr, All Upfront)

| Vehicle | m5.large discount | Flexibility |
|---|---|---|
| Standard RI | 60% | Locked (family, size, AZ, OS) |
| Convertible RI | 53% | Exchangeable within family+region |
| EC2 Instance SP | 72% | Flexible across sizes+AZs in family |
| Compute SP | 54% | Flexible across EC2+Fargate+Lambda |

Note: EC2 Instance SP discounts vary by instance family and may exceed
Standard RI discounts for some families. Always verify via Cost
Explorer for the specific family.

## Regional notes

- us-east-1, us-west-2, eu-west-1: baseline rates (shown above).
- ap-southeast-1, ap-northeast-1: ~5-10% higher on-demand rates.
- RI/SP discount percentages are roughly consistent across regions.
- The absolute $ savings are higher in more expensive regions.
- Always re-state rates from `aws ce get-cost-and-usage` for
  accurate savings in non-us-east-1 regions.
