# DR Strategy Deep Dive — Reference

This reference details the four canonical DR strategies with architecture
patterns, RTO/RPO targets, cost models, and per-component implementation
guidance. Use alongside the DR Failover Automator SKILL.md.

## Strategy 1 — Backup & Restore

**RTO:** hours to days. **RPO:** hours to days. **Cost:** 1x storage.

### Architecture
- Primary region: production workloads.
- Secondary region: AWS Backup vault with cross-region copies only.
- No running resources in the secondary until failover.

### Implementation
```bash
# Backup plan with cross-region copy
aws backup create-backup-plan --backup-plan '{
  "BackupPlanName": "cross-region-daily",
  "Rules": [{
    "RuleName": "DailyToSecondary",
    "TargetBackupVaultName": "Default",
    "ScheduleExpression": "cron(0 5 ? * * *)",
    "StartWindowMinutes": 60,
    "CompleteWindowMinutes": 1440,
    "CopyActions": [{
      "DestinationBackupVaultArn": "arn:aws:backup:us-west-2:111111111111:backup-vault:Default",
      "Lifecycle": {"DeleteAfterDays": 30}
    }]
  }]
}'
```

### Failover procedure
1. Trigger: manual (operator invokes restore).
2. Restore EBS snapshots, RDS snapshots, S3 (via Batch Operations).
3. Launch EC2 from restored AMIs.
4. Update Route 53 to point at secondary endpoints.
5. Verify application health.

### Best for
- Tier 3 applications (internal tools, archives).
- Dev/test environments where hours of downtime is acceptable.
- Compliance archives (long-term retention without running infra).

### Gotchas
- Restore time scales with snapshot size (1TB EBS = 30-60 min).
- Cross-region copy happens AFTER local backup completes — RPO includes
  copy time.
- No continuous replication — the secondary is cold until restore.

## Strategy 2 — Pilot Light

**RTO:** 10s of minutes to 1 hour. **RPO:** minutes.

### Architecture
- Primary region: full production.
- Secondary region: minimal running resources (DB replica, AMIs staged,
  launch templates ready). Scale to zero on compute; keep DB replica.

### Implementation
```bash
# Aurora Global Database (DB replica in secondary)
aws rds create-global-cluster --global-cluster-identifier my-global \
  --source-db-cluster-identifier arn:aws:rds:us-east-1:111111111111:cluster:my-primary \
  --region us-west-2

# EC2 AMIs staged via AWS Backup cross-region copy (not running)
# Launch templates pre-configured for scale-out
aws ec2 create-launch-template \
  --launch-template-name pilot-light-template \
  --launch-template-data file://lt-config.json
```

### Failover procedure
1. Trigger: Route 53 health check failure (automated) or manual.
2. Verify primary is down (Lambda + Step Functions with retries).
3. Promote Aurora Global secondary to primary (managed failover).
4. Scale out EC2 Auto Scaling Group from 0 to N instances.
5. Update Route 53 to secondary ALB.
6. Verify application health.

### Best for
- Tier 2 applications (periodic traffic, acceptable 30-min downtime).
- Cost-sensitive workloads that cannot afford full warm standby.
- Databases with low write volume (replication lag is minimal).

### Gotchas
- Aurora Global failover is < 1 min; EC2 scale-out adds 5-10 min.
- Total RTO = detection (90s) + verification (60s) + DB failover (60s) +
  scale-out (5-10 min) + DNS (60s TTL) = 10-15 min typical.
- The "pilot light" must be periodically tested — stale AMIs or broken
  launch templates surface only at failover.

## Strategy 3 — Warm Standby

**RTO:** single-digit minutes. **RPO:** seconds to minutes.

### Architecture
- Primary region: full production.
- Secondary region: scaled-down production (smaller instance types,
  fewer replicas, lower capacity). Always running, serving no live
  traffic.

### Implementation
```bash
# Secondary Aurora Global (always-on, read-only)
aws rds create-global-cluster --global-cluster-identifier my-global \
  --source-db-cluster-identifier arn:aws:rds:us-east-1:111111111111:cluster:my-primary \
  --region us-west-2

# Secondary EC2 Auto Scaling Group (min=2, smaller instance type)
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name warm-standby-asg \
  --launch-template LaunchTemplateName=warm-standby-template,Version=1 \
  --min-size 2 --max-size 20 --desired-capacity 2 \
  --vpc-zone-identifier subnet-aaa,subnet-bbb

# Secondary ALB (always-on, no traffic)
aws elbv2 create-load-balancer --name warm-standby-alb \
  --subnets subnet-aaa subnet-bbb
```

### Failover procedure
1. Trigger: Route 53 health check failure or manual.
2. Verify primary is down.
3. Promote Aurora Global secondary.
4. Scale up warm standby ASG (min=2 -> min=20).
5. Update Route 53 to secondary ALB.
6. Verify.

### Best for
- Tier 1 applications (production-critical, single-digit-minute RTO).
- Workloads with steady traffic that need fast failover.
- Databases that can tolerate async replication lag.

### Gotchas
- Cost: secondary runs at 50-100% of primary (always-on).
- Aurora Serverless v2 secondaries are cost-effective — scale to 0.5 ACU
  when idle, scales up when promoted.
- Warm standby must be load-tested — scale-up behavior under real
  traffic differs from idle scaling.

## Strategy 4 — Multi-Site Active/Active

**RTO:** near-zero. **RPO:** near-zero.

### Architecture
- Both regions serve live traffic simultaneously.
- Route 53 weighted or latency-based routing splits traffic.
- Database: DynamoDB Global Tables (multi-writer) or Aurora Global
  with application-level write routing.

### Implementation
```bash
# DynamoDB Global Tables (multi-region active-active)
aws dynamodb update-table \
  --table-name my-table \
  --replica-updates '[{"Create":{"RegionName":"us-west-2"}}]'

# Route 53 latency-based routing
aws route53 change-resource-record-sets --hosted-zone-id <zone-id> \
  --change-batch '{
    "Changes": [
      {"Action":"CREATE","ResourceRecordSet":{
        "Name":"app.example.com","Type":"A",
        "SetIdentifier":"us-east-1","Latency":{"Region":"us-east-1","Value":10},
        "AliasTarget":{"HostedZoneId":"Z2FDTNDATAQYW2",
          "DNSName":"alb-us-east-1.elb.amazonaws.com",
          "EvaluateTargetHealth":true}}},
      {"Action":"CREATE","ResourceRecordSet":{
        "Name":"app.example.com","Type":"A",
        "SetIdentifier":"us-west-2","Latency":{"Region":"us-west-2","Value":10},
        "AliasTarget":{"HostedZoneId":"Z2FDTNDATAQYW2",
          "DNSName":"alb-us-west-2.elb.amazonaws.com",
          "EvaluateTargetHealth":true}}}
    ]
  }'
```

### Failover procedure
1. Detect: Route 53 health check fails for one region.
2. Traffic automatically routes to the healthy region (no promotion
   needed — both are already active).
3. DynamoDB Global Tables reconcile writes (last-writer-wins default).
4. Aurora Global: failover the writer endpoint if the failed region
   had the primary.

### Best for
- Tier 0 applications (revenue-critical, near-zero downtime).
- Global applications serving users in multiple regions.
- Workloads designed for idempotent writes (multi-writer safety).

### Gotchas
- Cost: 200% of single-region (full duplicate).
- DynamoDB Global Tables last-writer-wins conflict resolution can lose
  writes under partition. Design for idempotency or use custom Lambda
  merge (2024-2025).
- Aurora Global multi-writer requires application-level conflict
  resolution — NOT automatic.

## Cost comparison

For a reference workload: 10 EC2 instances (t3.large), 1 Aurora cluster
(r6g.large, 1TB), 500GB S3, 100GB/month data transfer.

| Strategy | Primary cost/mo | Secondary cost/mo | Total |
|---|---|---|---|
| Backup & restore | $1,500 | $100 (storage only) | $1,600 |
| Pilot light | $1,500 | $300 (DB replica + AMIs) | $1,800 |
| Warm standby | $1,500 | $1,000 (scaled-down full) | $2,500 |
| Multi-site active/active | $1,500 | $1,500 (full duplicate) | $3,000 |

Actual costs vary by region, instance type, and data volume. Use AWS
Pricing Calculator for precise estimates.

## Game-day drill checklist

Run quarterly for any strategy above:

- [ ] Document the drill window (notify stakeholders).
- [ ] Snapshot current state (Route 53 records, ASG desired capacity,
      Aurora cluster status).
- [ ] Trigger failover (drill mode for DRS; managed planned failover
      for Aurora Global).
- [ ] Measure RTO (time from trigger to application serving traffic
      from secondary).
- [ ] Measure RPO (last replicated timestamp vs failover timestamp).
- [ ] Verify application functionality (smoke tests).
- [ ] Document the rollback path (secondary back to primary).
- [ ] Execute rollback.
- [ ] Post-mortem: what worked, what didn't, what to fix.

The first drill is the most valuable — it surfaces hidden issues
(stale AMIs, broken launch templates, missing IAM roles) that would
cause a real failover to fail.
