# Example usage: redshift-cluster-optimizer

A walkthrough showing the skill optimising an oversized RA3 cluster,
demonstrating the right-sizing analysis with CPUUtilization and
QueryQueueLength, pricing model evaluation, and the CONFIRM gate.

## Input (user prompt)

> Our Redshift analytics cluster seems oversized. It's a 4-node
> ra3.4xlarge running on On-Demand pricing. CPU averages 15% and queries
> never queue. Can you recommend optimisations?

```text
Cluster: analytics-prod-cluster
Region: us-east-1
NodeType: ra3.4xlarge
NumberOfNodes: 4
Pricing: On-Demand (no Reserved Nodes)
ClusterStatus: available

CloudWatch metrics (last 30 days):
  - CPUUtilization: avg=15%, max=30%
  - QueryQueueLength: avg=0, max=2
  - DatabaseConnections: avg=20, max=50

WLM: Auto WLM with SQA enabled, 2 queues (BI + ETL)
Concurrency Scaling: off
Storage: 12 TB managed storage (RA3)
Data sharing: not configured
```

## Skill output

```text
TARGET: analytics-prod-cluster
VERDICT: OPPORTUNITY_FOUND
REASON: ra3.4xlarge x 4 nodes at 15% CPU / 0 QueryQueueLength over 30 days is oversized (Step 2). No Reserved Node in place on steady-state production cluster (Step 3). On-Demand pricing on 24/7 workload.
RECOMMENDATION:
  Current: ra3.4xlarge x 4 at On-Demand in us-east-1
  Proposed: ra3.4xlarge x 2 at 3-yr Reserved Node in us-east-1
  Dimensions: right-size (4 -> 2 nodes), pricing model (On-Demand -> 3-yr RI)
  Confidence: HIGH — 30 days of CloudWatch data, clear utilization margins, 0 queue length confirms no contention.
ESTIMATED_SAVINGS:
  Monthly (right-size): $4,950.00 — ($3.39 x 2 x 730) = $4,949.40 (2 nodes removed)
  Monthly (pricing model): $1,484.82 — ($3.39 x 2 x 730) x 0.30 (3-yr RI at ~70% discount) = $1,484.82
  Annual total: ~$77,170.00 — ($4,949.40 + $1,484.82) x 12 = $77,170.64
  Assumptions: 730h/month, us-east-1 pricing as of 2026, workload steady-state, query performance verified post-downsize.
MIGRATION_STEPS:
  1. Snapshot the cluster:
     aws redshift create-snapshot --cluster-identifier analytics-prod-cluster --snapshot-identifier pre-rightsize-$(date +%s)
  2. Resize (elastic resize, ~10-20 min downtime):
     aws redshift resize-cluster --cluster-identifier analytics-prod-cluster --cluster-type multi-node --number-of-nodes 2 --node-type ra3.4xlarge
  3. Monitor CPUUtilization and QueryQueueLength for 7 days. Roll back if CPU > 80% or QueueLength > 50.
  4. After 7 days stable, purchase 3-yr Reserved Nodes:
     aws redshift describe-reserved-nodes --node-type ra3.4xlarge --duration 94608000 --offering-type "No Upfront"
     aws redshift purchase-reserved-node-offering --reserved-node-offering-id <offering-id> --node-count 2
CONFIRM: Before resizing the cluster, emit and await: "CONFIRM: About to resize analytics-prod-cluster from 4 to 2 ra3.4xlarge nodes in us-east-1. Elastic resize causes brief downtime (~10-20 min). Proceed? (yes/no)"
```

## What the skill caught that a generic assistant misses

1. **QueryQueueLength validation.** A generic assistant might recommend
   downsizing based on CPU alone. The skill requires both CPUUtilization
   AND QueryQueueLength — 0 queue depth confirms the low CPU is genuine
   overprovisioning, not a WLM bottleneck.

2. **Stacked savings.** The skill stacks right-sizing (reduce nodes)
   with pricing model (Reserved Nodes on the remaining 2 nodes) for
   compounding savings. A generic assistant recommends one or the other.

3. **Reserved Node purchase after right-sizing.** The skill sequences
   the RI purchase AFTER the right-size verification — buying an RI for
   4 nodes then downsizing to 2 wastes the RI. A generic assistant
   doesn't consider this ordering.

4. **Post-downsize verification window.** The skill mandates 7 days of
   monitoring before committing to the RI purchase. A generic assistant
   skips this safety step.

5. **Snapshot before resize.** The skill emits the snapshot CLI as step
   1 for rollback. A generic assistant jumps straight to the resize.

## Slash-command invocation

```
/aws:optimize-redshift-cluster
```

Or via the orchestrator:

```
/aws:pipeline
You: "optimise our Redshift analytics cluster cost"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: redshift-cluster-optimizer]` and hands
off to this skill for the optimisation block.

## Live-account follow-up (optional, requires AWS CLI)

After the right-size completes, verify cluster health:

```bash
# Confirm cluster is available with new node count
aws redshift describe-clusters \
  --cluster-identifier analytics-prod-cluster \
  --query 'Clusters[0].{Status:ClusterStatus, NodeType:NodeType, Nodes:NumberOfNodes}' \
  --output json

# Check CPUUtilization post-downsize
aws cloudwatch get-metric-statistics \
  --namespace AWS/Redshift \
  --metric-name CPUUtilization \
  --dimensions Name=ClusterIdentifier,Value=analytics-prod-cluster \
  --start-time $(date -u -d '7 days ago' +%FT%TZ 2>/dev/null || date -u -v7d +%FT%TZ) \
  --end-time $(date +%FT%TZ) \
  --period 3600 --statistics Average,Maximum --output json

# Verify RI coverage
aws redshift describe-reserved-nodes --status active --output json
```

If CPU exceeds 80% or QueryQueueLength exceeds 50, roll back by resizing
back to 4 nodes.
