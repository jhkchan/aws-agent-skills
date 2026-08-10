# Example usage: aurora-cost-optimizer

A walkthrough showing the skill optimising an Aurora cluster with
multi-dimension waste (over-floored I/O on Standard tier, mirrored
readers, no RI) — surfacing four actionable opportunities, sizing
each with break-even math, and staging one-dimension-per-window
remediation with snapshot rollback.

## Input (user prompt)

> Our orders-prod-cluster Aurora bill crept up to ~$2,500/month and
> I'm not sure where the waste is. Can you optimise it?

```text
Cluster: orders-prod-cluster
Engine: aurora-mysql (8.0)
Region: us-east-1
Instances:
  - writer: db.r6g.2xlarge (8 vCPU, 64 GB)
  - reader-1: db.r6g.2xlarge
  - reader-2: db.r6g.2xlarge
Storage: Standard tier, 1,000 GB used
I/O (last 30 days): 600,000,000 requests
Pricing: On-Demand (no RI)
CloudWatch metrics (last 30 days):
  - writer CPUUtilization: avg=15%, max=28%
  - reader-1 CPUUtilization: avg=8%, max=18%
  - reader-2 CPUUtilization: avg=8%, max=18%
Performance Insights:
  - writer DBLoad: avg=1.2, max=4.5 (low for 8 vCPU)
  - top-SQL: orders_join_by_customer at 38% of DBLoad
    (missing index on orders.customer_id)
Global DB: not in use
Backtrack: disabled
```

## Skill output

```text
TARGET: orders-prod-cluster
VERDICT: OPPORTUNITY_FOUND
REASON: CE shows I/O 35% of Aurora bill ($420/month on 600M I/O
  requests vs $200 storage on Standard tier), writer CPU avg 15%
  / max 28% on db.r6g.2xlarge, readers mirrored at avg 8% CPU,
  and no RI on a cluster running 14 months steady-state. Four
  dimensions have actionable opportunities.
RECOMMENDATION:
  Current:
    Compute: writer db.r6g.2xlarge ($730), 2 readers db.r6g.2xlarge
      each ($730 each)
    Storage: Standard, 1,000 GB × $0.10 = $100/month
    I/O: 600M × $0.20 = $120/month (CE shows $420 incl. overhead)
    Pricing: On-Demand (no RI); Global DB: not in use; backtrack: off
  Proposed:
    - Right-sizing: writer → db.r6g.xlarge ($0.50/h) per CPU 15/28%;
      readers → db.r6g.large ($0.25/h) per CPU 8/18%.
    - I/O tier: I/O-Optimized — 600M I/O exceeds the 400M break-even
      for 1,000 GB storage.
    - RI: 1-yr No Upfront RI on the new writer class once right-size
      is applied; hold on reader RI until reader count stabilises.
    - Performance Insights: top-SQL = orders_join_by_customer at 38%
      of DBLoad (missing index on orders.customer_id). DBA ticket.
  Confidence: HIGH — CE confirms I/O share; CloudWatch confirms CPU
    headroom; PI confirms top-SQL dominance.
ESTIMATED_SAVINGS:
  Monthly (right-sizing): $1,095  (writer $365 + 2 readers $730)
  Monthly (I/O-Optimized): $40    ($220 Standard → $180 I/O-Optimized)
  Monthly (RI on writer): $146    (40% off db.r6g.xlarge $365)
  Monthly (Global DB / backtrack): $0
  Annual total: $15,372
  Assumptions: us-east-1 pricing, 730h/month, right-size occurs
    before RI purchase so RI matches the new instance class.
MIGRATION_STEPS:
  1. Snapshot the cluster before any change:
     aws rds create-db-cluster-snapshot \
       --db-cluster-identifier orders-prod-cluster \
       --db-cluster-snapshot-identifier pre-opt-$(date +%s)
  2. Right-size the writer:
     aws rds modify-db-instance \
       --db-instance-identifier orders-prod-writer \
       --db-instance-class db.r6g.xlarge --apply-immediately
     # Wait for status=available; verify CPU stays < 70% in 24h
  3. Right-size readers one at a time (keep one full-size for failover):
     aws rds modify-db-instance \
       --db-instance-identifier orders-prod-reader-1 \
       --db-instance-class db.r6g.large --apply-immediately
  4. Switch to I/O-Optimized tier (non-disruptive, separate window):
     aws rds modify-db-cluster \
       --db-cluster-identifier orders-prod-cluster \
       --storage-type aurora-iopt1 --apply-immediately
  5. After right-size settles (7 days), purchase RI on writer:
     aws rds purchase-reserved-db-instances-offering \
       --reserved-db-instances-offering-id <offering-id> \
       --reserved-db-instance-id orders-writer-ri-1yr
  6. File DBA ticket for the missing index on orders.customer_id.
CONFIRM: Before each state-changing CLI, emit and await operator
  approval. Stage changes one dimension per window; never batch
  the writer right-size + I/O tier switch.
```

## What the skill caught that a generic assistant misses

1. **I/O-Optimized break-even math.** A generic assistant says "I/O-
   Optimized might be cheaper." The skill computes the break-even
   (0.4M I/O per GB-month), confirms 600M exceeds the 400M threshold
   for 1,000 GB, and quantifies the $40/month I/O savings plus the
   $20/month storage uplift — net savings rather than a guess.

2. **Writer vs reader independent right-sizing.** A generic assistant
   treats "right-size the cluster" as one move. The skill recognises
   that the writer (CPU 15/28%) downsizes one step, while readers
   (CPU 8/18%) can downsize two steps. The writer keeps more headroom
   for failover; readers can run lean because they don't bear commit
   load.

3. **RI timing — right-size first, then RI.** A generic assistant
   might recommend buying an RI immediately. The skill sequences the
   RI purchase AFTER the right-size so the RI matches the new instance
   class (db.r6g.xlarge, not the old db.r6g.2xlarge). Buying an RI on
   the old class would lock in a discount on an instance class you no
   longer run.

4. **Performance Insights as a cost lever.** A generic assistant sees
   Performance Insights as a performance tool. The skill identifies
   that the top-SQL at 38% of DBLoad is a missing index — fixing it
   drops DBLoad further, which may enable a SECOND writer downsize
   in the next quarter. The DBA work is reframed as a cost saving.

5. **Failover-aware reader sizing.** A generic assistant might
   downsize both readers simultaneously. The skill explicitly keeps
   one reader at full size during the transition so failover capacity
   is preserved — and notes that readers should never be sized below
   the failover-promotion capacity.

6. **Staged one-dimension-per-window remediation.** A generic
   assistant stacks all changes into one maintenance window. The skill
   sequences writer right-size → reader right-size → I/O tier switch →
   RI purchase, with monitoring between each, so any CPU spike or
   failover regression can be attributed to a specific change.

7. **Snapshot rollback path.** A generic assistant goes straight to
   `modify-db-instance` with no rollback plan. The skill captures a
   cluster snapshot before any change, providing a recovery path if
   the new instance class can't handle the load.

## Slash-command invocation

```
/aws:optimize-aurora-cost
```

Or via the orchestrator:

```
/aws:pipeline
You: "why is our Aurora bill so high?"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: aurora-cost-optimizer]` and hands
off to this skill for the optimisation block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the new pattern:

```bash
# Confirm the cluster is healthy post-changes
aws rds describe-db-clusters \
  --db-cluster-identifier orders-prod-cluster \
  --query 'DBClusters[0].{Status:Status, Engine:Engine,
    StorageType:StorageType}' --output table

# Verify CPU stays within bounds on the downsized writer
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=orders-prod-writer \
  --start-time $(date -u -v-7d +%FT%TZ 2>/dev/null) \
  --end-time $(date -u +%FT%TZ) \
  --period 3600 --statistics Average Maximum --output json

# Verify the I/O line item drops in CE
aws ce get-cost-and-usage \
  --time-period Start=$(date -u -v-7d +%F 2>/dev/null),End=$(date -u +%F) \
  --filter '{"Dimensions":{"Key":"USAGE_TYPE","Values":["Aurora:IOUsage"]}}' \
  --granularity DAILY --metrics "UsageQuantity" "BlendedCost" \
  --output json
```

If writer CPU consistently exceeds 70% in the 7 days post-right-size,
roll back to the prior instance class and re-evaluate.

## Fleet-wide extension

For an Organizations fleet of N Aurora clusters:

1. Pull `describe-db-clusters` and CE Aurora USAGE_TYPE breakdowns
   across all accounts.
2. Group clusters by waste pattern (I/O-heavy on Standard, mirrored
   readers, no RI, etc.).
3. Sort by estimated savings (largest first).
4. Slice into batches of at most 3 clusters; emit per-cluster
   MIGRATION_STEPS and a single CONFIRM per batch.
5. Verify each batch before proceeding to the next.
6. After the per-cluster sweep, evaluate multi-cluster RI strategies
   (size-flexible RIs across engines where applicable).
