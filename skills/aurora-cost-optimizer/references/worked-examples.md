# Worked Examples — Aurora Cost Optimizer

Load-on-demand worked examples moved verbatim from SKILL.md.

## Step 4 — writer + reader right-sizing


Cluster with writer `db.r6g.2xlarge` ($1.00/h in us-east-1) and two
readers `db.r6g.2xlarge` (mirrored). Writer CPU avg=15%, max=28%;
readers CPU avg=8%, max=18%. Right-size writer to `db.r6g.xlarge`
($0.50/h) and readers to `db.r6g.large` ($0.25/h):
- Writer: ($1.00 - $0.50) × 730h = $365/month
- Each reader: ($1.00 - $0.25) × 730h = $547.50/month
- Total monthly savings: $365 + $547.50 × 2 = $1,460/month
- Trade-off: writer has less headroom for traffic spikes. Confirm max
  CPU stays < 70% after the downsize; otherwise keep writer at 2xlarge.

## Step 5 — Serverless v2 ACU floor


Cluster with MinCapacity=8, MaxCapacity=32, avg ACU=4.5 over 30 days,
peak ACU=14. Drop MinCapacity to 2 (MaxCapacity stays at 32):
- Current floor: 8 ACU × $0.12 × 730h = $700.80/month minimum
- New floor: 2 ACU × $0.12 × 730h = $175.20/month minimum
- Actual billed ACU drops by ~3.5 ACU average → ~3.5 × $0.12 × 730 =
  $306.60/month savings
- Trade-off: sub-second response on cold-start; verify p99 latency
  stays within SLA during scale-up events.

## Step 6 — I/O-Optimized migration


Aurora PostgreSQL cluster, 1,000 GB storage, 600M I/O requests/month.
- Standard: 1,000 × $0.10 + 600 × $0.20 = $100 + $120 = $220/month
- I/O-Optimized: 1,000 × $0.18 + $0 = $180/month
- Monthly savings: $40
- Annual savings: $480
- Switch with `modify-db-cluster --storage-type aurora-iopt1` (Aurora
  PostgreSQL 14+/MySQL 8+); non-disruptive, takes effect within minutes.

If I/O is only 200M/month, Standard stays cheaper:
- Standard: $100 + $40 = $140
- I/O-Optimized: $180
- Stay on Standard.

## Worked example — already optimal

```text
TARGET: reporting-cluster-prod
VERDICT: ALREADY_OPTIMAL
REASON: All seven dimensions verified at cost-optimal config:
  Aurora I/O-Optimized enabled; Serverless v2 Min=2/Max=16 with
  steady ACU 6-10; writer and readers rightsized to CPU avg 45%;
  1-yr RI on writer and primary reader; no Global DB waste; no
  backtrack; Performance Insights top-SQL evenly distributed.
RECOMMENDATION:
  Current: All dimensions optimal
  Proposed: no change
  Confidence: HIGH — CE confirms 30-day spending pattern stable;
    Performance Insights shows no dominant SQL.
ESTIMATED_SAVINGS:
  Monthly (all dimensions): $0
  Annual total: $0
MIGRATION_STEPS:
  - None required. Continue monthly CE review.
  - Re-evaluate at next growth forecast — Serverless v2 Max may
    need to scale if reader count doubles.
```

### Worked example — already optimal

```text
TARGET: reporting-cluster-prod
VERDICT: ALREADY_OPTIMAL
REASON: All seven dimensions verified at cost-optimal config:
  Aurora I/O-Optimized enabled; Serverless v2 Min=2/Max=16 with
  steady ACU 6-10; writer and readers rightsized to CPU avg 45%;
  1-yr RI on writer and primary reader; no Global DB waste; no
  backtrack; Performance Insights top-SQL evenly distributed.
RECOMMENDATION:
  Current: All dimensions optimal
  Proposed: no change
  Confidence: HIGH — CE confirms 30-day spending pattern stable;
    Performance Insights shows no dominant SQL.
ESTIMATED_SAVINGS:
  Monthly (all dimensions): $0
  Annual total: $0
MIGRATION_STEPS:
  - None required. Continue monthly CE review.
  - Re-evaluate at next growth forecast — Serverless v2 Max may
    need to scale if reader count doubles.
```
