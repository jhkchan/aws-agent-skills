# Eval prompt: drs-ec2-recovery

Design a DR failover plan using AWS Elastic Disaster Recovery (DRS) for
20 stateful EC2 instances. Emit the standard DR block.

Requirements:
- Application tier: compute (EC2 stateful)
- RTO target: 60 minutes
- RPO target: 15 minutes
- Primary region: us-east-1
- Secondary region: us-west-2
- Strategy: pilot light with Elastic DRS
- DRS: non-blocking agent installed on all 20 source servers, continuous
  block-level replication to staging area in us-west-2
- Launch templates configured per source server (instance type, subnet,
  security group, IAM role, tags)
- Drill: run quarterly with is_drill=true in isolated subnet
  (dedicated drill SG, no production traffic)
- Orchestration: Step Functions state machine with:
  1. Kill-switch check (Parameter Store /dr/kill-switch)
  2. Verify-primary-down Lambda (3 retries)
  3. DRS launch (drs start-recovery, all 20 source servers, is_drill=false)
  4. Route 53 UPSERT to secondary ALB
  5. Verify-secondary-up Lambda (smoke test all 20 instances)
  6. Notify via SNS
  7. Human approval via SQS task token
- DNS: Route 53 failover record, TTL 60s, health check threshold=3
- Game-day drill: 2026-07-20, RTO measured 45min, RPO 5min

Expected: AUTOMATED. The DRS-based failover covers continuous replication
via non-blocking agent, pre-configured launch templates, Step Functions
orchestration with kill-switch + verification + drill mode, and a tested
game-day drill validating RTO/RPO.
