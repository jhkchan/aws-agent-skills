# Fargate Pricing Matrix — Reference

Supplementary reference for the Fargate Cost Optimizer skill. Detailed
pricing for all CPU/memory combinations, Spot vs On-Demand, x86_64 vs
ARM64, and regional rate notes.

## Fargate allowed CPU/memory combinations

| CPU (vCPU) | Memory range (GB) |
|---|---|
| 0.25 | 0.5, 1, 2 |
| 0.5 | 1, 2, 3, 4 |
| 1 | 2, 3, 4, 5, 6, 7, 8 |
| 2 | 4 through 16 (1 GB increments) |
| 4 | 8 through 30 (1 GB increments) |
| 8 | 16 through 60 (1 GB increments) |
| 16 | 32 through 120 (1 GB increments) |

## Pricing: x86_64 On-Demand (us-east-1, 2026, USD per hour)

| CPU | Memory | Hourly | Monthly (730h) |
|---|---|---|---|
| 0.25 | 0.5 GB | $0.01096 | $7.99 |
| 0.25 | 1 GB | $0.01162 | $8.48 |
| 0.25 | 2 GB | $0.01294 | $9.45 |
| 0.5 | 1 GB | $0.02162 | $15.78 |
| 0.5 | 2 GB | $0.02324 | $16.97 |
| 0.5 | 4 GB | $0.02648 | $19.33 |
| 1 | 2 GB | $0.04324 | $31.57 |
| 1 | 4 GB | $0.04648 | $33.93 |
| 1 | 8 GB | $0.05296 | $38.66 |
| 2 | 4 GB | $0.08648 | $63.13 |
| 2 | 8 GB | $0.09296 | $67.86 |
| 2 | 16 GB | $0.10592 | $77.32 |
| 4 | 8 GB | $0.17296 | $126.26 |
| 4 | 16 GB | $0.18592 | $135.72 |
| 4 | 30 GB | $0.21184 | $154.64 |
| 8 | 16 GB | $0.34592 | $252.52 |
| 8 | 30 GB | $0.37184 | $271.44 |
| 8 | 60 GB | $0.42368 | $309.29 |
| 16 | 32 GB | $0.69184 | $505.04 |
| 16 | 60 GB | $0.74368 | $542.89 |
| 16 | 120 GB | $0.84736 | $618.57 |

## Pricing: ARM64 On-Demand (us-east-1, 2026, USD per hour)

ARM64 (Graviton) is approximately 20% cheaper than x86_64 across all
combos.

| CPU | Memory | Hourly | Monthly (730h) |
|---|---|---|---|
| 0.25 | 0.5 GB | $0.00877 | $6.40 |
| 0.5 | 1 GB | $0.01730 | $12.63 |
| 1 | 2 GB | $0.03460 | $25.26 |
| 1 | 4 GB | $0.03720 | $27.16 |
| 2 | 4 GB | $0.06920 | $50.52 |
| 2 | 8 GB | $0.07440 | $54.31 |
| 4 | 8 GB | $0.13840 | $101.03 |
| 4 | 16 GB | $0.14880 | $108.62 |
| 8 | 16 GB | $0.27680 | $202.06 |
| 8 | 32 GB | $0.29760 | $217.25 |

## Pricing: Fargate Spot (approximate, us-east-1, 2026)

Spot pricing is approximately 70% off On-Demand for both x86_64 and
ARM64.

| Config (x86_64) | On-Demand hourly | Spot hourly | Spot savings |
|---|---|---|---|
| 0.25 vCPU / 0.5 GB | $0.01096 | ~$0.0033 | 70% |
| 1 vCPU / 2 GB | $0.04324 | ~$0.0130 | 70% |
| 2 vCPU / 4 GB | $0.08648 | ~$0.0259 | 70% |
| 4 vCPU / 8 GB | $0.17296 | ~$0.0519 | 70% |

ARM64 Spot is approximately 76% cheaper than x86_64 On-Demand.

## Savings Plans discount rates (approximate)

| Commitment | Discount vs On-Demand |
|---|---|
| 1-year, no upfront | ~20% |
| 1-year, all upfront | ~28% |
| 3-year, no upfront | ~38% |
| 3-year, all upfront | ~48% |

Compute Savings Plans apply to Fargate, EC2, and Lambda combined.

## Stacking savings

| Combination | Cumulative discount vs x86_64 On-Demand |
|---|---|
| Right-size (2 vCPU → 1 vCPU) | ~50% (halves the base) |
| Right-size + ARM64 | ~60% |
| Right-size + ARM64 + Spot | ~85% |
| Right-size + ARM64 + Spot + SP | ~88% |

## Regional notes

- us-east-1, us-west-2, eu-west-1: baseline rates (shown above).
- ap-southeast-1, ap-northeast-1: ~5-10% higher.
- sa-east-1: ~15-20% higher.
- Re-state regional rates from `aws ce get-cost-and-usage` for
  accurate savings in non-us-east-1 regions.

## Savings estimation — x86_64 On-Demand (moved from SKILL.md)

**Savings estimation (us-east-1, On-Demand, x86_64, 2026):**

| Config | Hourly rate | Monthly (730h) |
|---|---|---|
| 0.25 vCPU / 0.5 GB | $0.011 | $8.03 |
| 0.5 vCPU / 1 GB | $0.022 | $16.06 |
| 1 vCPU / 2 GB | $0.043 | $31.39 |
| 2 vCPU / 4 GB | $0.087 | $63.51 |
| 4 vCPU / 8 GB | $0.173 | $126.29 |
| 8 vCPU / 16 GB | $0.346 | $252.58 |

Dropping from 2 vCPU / 4 GB to 1 vCPU / 2 GB saves ~$32/task/month.
