# Advanced Patterns (load on demand) — EC2 Reserved Capacity Optimizer

Mindset principles, the commitment-layering expert heuristic, the configuration dependency graph, the RI Marketplace selling decision checklist, and 2024-2026 feature notes, moved verbatim from SKILL.md.


---

## Mindset — utilization vs coverage, Standard vs Convertible, SP mechanics (moved from SKILL.md)

**One-line takeaway:** EC2 commitment optimization is about matching
the right commitment vehicle (Standard RI, Convertible RI, Compute SP,
EC2 Instance SP) to the right workload segment (steady-state baseline,
flexible family, cross-service compute), then sizing the commitment to
the observed baseline — not the peak, not the current spend. The
3-year Standard RI is the deepest discount (~72% vs on-demand), but
only safe for instance types locked in for 3 years. Savings Plans give
flexibility at slightly less discount. The optimal portfolio layers
both.

Three facts make EC2 commitment optimization different from generic
cost reduction:

- **RI utilization and coverage are independent metrics.** Utilization
  measures whether your committed RIs are being consumed (you paid for
  them, are you using them?). Coverage measures whether your running
  instances are covered by RIs (you are running them, did you commit?).
  Low utilization means you over-committed. Low coverage means you
  under-committed. Both waste money in different ways.
- **Standard RIs cannot be exchanged; Convertible RIs can.** A Standard
  RI locks the instance family, type, AZ, and OS for the full term. A
  Convertible RI allows exchange to a different instance type within
  the same instance family and region, providing a hedge against
  workload changes. The trade-off: Convertible RIs cost ~10% less
  discount than Standard.
- **Savings Plans apply automatically by spend, not by instance.**
  Compute SP covers any EC2, Fargate, or Lambda spend up to a
  committed $/hour. EC2 Instance SP covers a specific instance family
  in a region, more like an RI but with flexibility across sizes and
  AZs. No reservation assignment is needed — AWS applies the discount
  automatically.

## Expert heuristic — 3yr Standard bedrock, SP flexible layer, on-demand spike (moved from SKILL.md)

Three rules, in order, produce 90% of commitment savings:

1. **Commit the bedrock with 3-year Standard RIs.** The always-on,
   never-changing core of the fleet (databases, persistent API servers,
   management nodes) gets the deepest discount with 3-year Standard
   RIs, All Upfront. This is ~72% off on-demand. The criterion: the
   instance type must have been running 24/7 for 90+ days with no
   planned migration.

2. **Layer a Compute SP for the flexible compute.** On top of the
   bedrock, add a Compute SP covering the semi-stable services that
   may change instance families (Graviton migration), cross services
   (EC2 to Fargate), or scale. The SP provides ~48% off with full
   flexibility. Size the SP to the steady-state baseline minus the RI
   bedrock.

3. **Leave the spike on on-demand or Spot.** Variable, unpredictable,
   and scaling portions of the fleet stay on on-demand or Spot. Never
   commit to the peak — you will over-commit and waste. Commit to the
   floor, not the ceiling.

**The Convertible RI exchange is the secret weapon.** When a workload
shifts within the same instance family (e.g., m5.large to m5.xlarge),
a Convertible RI can be exchanged at no cost. Standard RIs cannot. For
semi-stable workloads, the ~10% lower discount on Convertible is worth
the exchange flexibility.

## Configuration dependency graph (moved from SKILL.md)

```
EC2 Fleet (describe-instances)
  |
  +-- Cost Explorer Spend (get-cost-and-usage)
  |     |
  |     +-- RI Utilization (get-reservation-utilization)
  |     |     |
  |     |     +-- [UTILIZATION_GAP] -> Sell RI (Marketplace) / Exchange (Convertible)
  |     |
  |     +-- RI Coverage (get-reservation-coverage)
  |     |     |
  |     |     +-- [COVERAGE_GAP] -> Purchase Recommendation (get-reservation-purchase-recommendation)
  |     |           |
  |     |           +-- TERM_EVAL -> 1yr vs 3yr decision
  |     |           +-- PAYMENT_EVAL -> Upfront vs No-Upfront decision
  |     |
  |     +-- SP Utilization (get-savings-plans-utilization)
  |     |     |
  |     |     +-- [UTILIZATION_GAP] -> Let expire / Recommit lower
  |     |
  |     +-- SP Coverage (get-savings-plans-coverage)
  |           |
  |           +-- [COVERAGE_GAP] -> SP Purchase Recommendation (get-savings-plans-purchase-recommendation)
  |                 |
  |                 +-- VEHICLE_EVAL -> Compute SP vs EC2 Instance SP vs RI
  |
  +-- CloudWatch / Budgets -> Utilization alerts (80% investigate, 60% act)
```

## RI Marketplace selling (moved from SKILL.md)

Standard RIs that are underutilized can be listed on the RI Marketplace
for sale. Convertible RIs can also be sold.

**Marketplace decision checklist:**

| Remaining term | Recommendation | Rationale |
|---|---|---|
| < 1 month | Do not sell | Marketplace 12% fee + low remaining value = net loss |
| 1-6 months | Evaluate | Compare sell proceeds vs letting it expire |
| 6-18 months | List for sale | Good remaining value; can recover significant commitment |
| > 18 months | List or exchange | If Convertible: exchange to current type. If Standard: sell |

```bash
# List a Standard RI for sale on the Marketplace:
aws ec2 describe-reserved-instances-modifications \
  --reserved-instances-ids <ri-id>

# Check Marketplace listings:
aws ec2 describe-reserved-instances-listings
```

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **EC2 Instance Savings Plans (2024-2025):** A newer SP type that
  commits to an instance family in a region with flexibility across
  sizes and AZs. Offers discounts comparable to Standard RIs (~72% on
  3yr All Upfront) but with significantly more flexibility. Replaces
  the need for Zonal RIs in many use cases.
- **Savings Plans recommendation improvements (2024-2026):** Cost
  Explorer now provides SP recommendations with flexible lookback
  periods (7, 30, 60 days) and cross-account aggregation for
  Organizations payer accounts.
- **Convertible RI exchange automation (2024-2025):** The GetConvertibleReservedInstancesExchangeQuote
  API now returns richer exchange options, including cross-AZ and
  cross-size exchanges within the same family and region.
- **RI Marketplace improvements (2025-2026):** The RI Marketplace now
  supports partial-term sales and simplified listing for Convertible
  RIs, making it easier to recover value from underutilized
  commitments.
- **Budgets RI/SP tracking (2024-2026):** AWS Budgets now supports
  RI/SP utilization and coverage budgets, enabling proactive alerts
  when commitments fall below threshold.
