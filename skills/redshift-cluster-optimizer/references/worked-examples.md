# Worked Examples — Redshift Cluster Optimisation

The primary example (analytics-prod-cluster: right-size + Reserved
Node + compression) lives in SKILL.md under "Perfect example output".

### Worked example — DC2.Large to RA3.xlplus node-type migration

```text
TARGET: billing-events-cluster (arn:aws:redshift:us-east-1:123456789012:cluster:billing-events-cluster)
VERDICT: OPPORTUNITY_FOUND
REASON: dc2.large x 12 nodes at 12% CPU / 0 QueryQueueLength over 30 days is
  massively oversized — 12 nodes exist solely because data grew to 1.5 TB
  and each dc2.large holds only 160 GB local (Step 1). Migrating to
  ra3.xlplus x 2 with managed storage eliminates 10 excess compute nodes.
  No Reserved Node in place on steady-state production (Step 3). Largest
  table (events_log, 1.2 TB) has no sort key — every query scans the full
  table (Step 5).
RECOMMENDATION:
  Current: dc2.large x 12 at On-Demand in us-east-1
    Distribution: KEY(user_id) on 6 tables, EVEN on 4 tables  Sort key: none on events_log
  Proposed: ra3.xlplus x 2 at 3-yr Reserved Node in us-east-1
    Distribution: KEY(tenant_id) on all tables  Sort key: compound(event_time, tenant_id) on events_log
  Dimensions: node-type (dc2.large → ra3.xlplus), right-size (12 → 2),
    pricing (On-Demand → 3-yr RI), distribution (KEY user_id → KEY tenant_id),
    sort-key (none → compound), storage (VACUUM + compress)
  Confidence: HIGH — 30 days of CloudWatch data; 12% CPU / 0 queue confirms
    overprovisioning; storage at 73% of local capacity confirms node-count
    driven by storage growth not compute need.
ESTIMATED_SAVINGS:
  Monthly (node-type + right-size): $1,680.46
    — dc2.large: 12 × $0.25 × 730 = $2,190.00
    — ra3.xlplus OD: 2 × $0.775 × 730 = $1,131.50
    — node saving: $2,190.00 − $1,131.50 = $1,058.50
  Monthly (pricing model): $452.60
    — ra3.xlplus 3-yr RI (~60% discount): 2 × $0.31 × 730 = $452.60
    — vs On-Demand for remaining 2 nodes: $1,131.50 − $452.60 = $678.90 saved
      (pricing discount applied to proposed nodes only)
  Monthly (managed storage): -$36.00
    — 1,500 GB × $0.024/GB = $36.00 (new cost; DC2 storage was bundled)
  Monthly (storage compression): $14.40
    — VACUUM reclaims est. 600 GB soft-deleted rows × $0.024 = $14.40
  Monthly total: $2,107.46  ($1,058.50 + $678.90 + $36.00 offset + $14.40)
  Annual total: ~$25,289.52
  Assumptions: 730h/month, us-east-1 pricing as of 2026, 3-yr RI No Upfront
    at ~60% discount, managed storage at $0.024/GB-month, workload steady-state.
MIGRATION_STEPS:
  1. Snapshot the cluster before migration:
     aws redshift create-snapshot --cluster-identifier billing-events-cluster \
       --snapshot-identifier pre-dc2-ra3-migration-$(date +%s) --region us-east-1
  2. Elastic resize to ra3.xlplus x 2 (brief downtime ~10-20 min):
     aws redshift resize-cluster --cluster-identifier billing-events-cluster \
       --cluster-type multi-node --number-of-nodes 2 --node-type ra3.xlplus \
       --region us-east-1
  3. Wait for resize to complete, then verify query performance:
     aws redshift describe-clusters --cluster-identifier billing-events-cluster \
       --query 'Clusters[0].ClusterStatus' --output text --region us-east-1
  4. Update distribution style on key tables:
     ALTER TABLE events_log ALTER DISTSTYLE KEY DISTKEY (tenant_id);
     ALTER TABLE user_sessions ALTER DISTSTYLE KEY DISTKEY (tenant_id);
  5. Add compound sort key to events_log:
     ALTER TABLE events_log ALTER SORTKEY (event_time, tenant_id);
     VACUUM SORT ONLY events_log;
  6. VACUUM and ANALYZE all tables:
     VACUUM DELETE; ANALYZE;
  7. After 7 days of stable operation, purchase 3-yr Reserved Nodes:
     aws redshift describe-reserved-node-offerings --node-type ra3.xlplus \
       --duration 94608000 --offering-type "No Upfront" --region us-east-1
     aws redshift purchase-reserved-node-offering \
       --reserved-node-offering-id <offering-id> --node-count 2 --region us-east-1
CONFIRM: Before migrating billing-events-cluster from dc2.large x 12 to
  ra3.xlplus x 2 in us-east-1, emit and await: "CONFIRM: Elastic resize
  causes ~10-20 min downtime. Monthly saving $2,107.46 (96% compute
  reduction). Proceed? (yes/no)"
```
