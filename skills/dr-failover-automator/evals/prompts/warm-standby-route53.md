# Eval prompt: warm-standby-route53

Design a warm-standby DR strategy for our production API. Emit the
standard DR block.

Requirements:
- Application tier: app + DB
- RTO target: 5 minutes
- RPO target: 1 minute
- Primary region: us-east-1
- Secondary region: us-west-2
- Strategy: warm standby
- Secondary: always-on scaled-down (2x t3.medium EC2, Aurora Serverless
  v2 at 0.5 ACU minimum)
- Database: Aurora Global Database (async replication, ~1s lag)
- DNS: Route 53 failover record, TTL 60s, health check HTTPS /health
  on primary ALB, interval=30s, threshold=3
- Global Accelerator in front of both regional ALBs for sub-second
  client failover (anycast IPs, traffic-dial 100/0 primary/secondary)
- Orchestration: Step Functions with kill-switch
  (Parameter Store /dr/kill-switch), verify-primary-down Lambda,
  promote secondary (Aurora managed failover), flip Global Accelerator
  traffic dial, verify-secondary-up Lambda, SQS task-token human
  approval
- Game-day drill: 2026-08-01, RTO measured 4min
- Resilience Hub assessment score: 88

Expected: AUTOMATED. The warm-standby design covers RTO/RPO targets
with always-on secondary, Route 53 + Global Accelerator for DNS-level
failover, Step Functions orchestration with kill-switch and verification,
and a tested game-day drill validating the RTO.
