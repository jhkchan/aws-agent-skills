# Eval prompt: pilot-light-aurora-global

Design a DR failover plan for our three-tier web application. Emit the
standard DR block (STRATEGY, FAILOVER, ORCHESTRATION, VERIFICATION,
VERDICT, FINDINGS, REMEDIATION).

Requirements:
- Application tier: mixed (web, app, DB)
- RTO target: 30 minutes
- RPO target: 5 minutes
- Primary region: us-east-1
- Secondary region: us-west-2
- Strategy: pilot light
- Database: Aurora Global Database (managed planned failover via
  failover-global-cluster)
- Compute: EC2 Auto Scaling Group in secondary (scale from 0 to 10 on
  failover), launch templates pre-configured
- DNS: Route 53 failover record with health check (HTTPS /health on
  primary ALB, interval=30s, threshold=3, TTL 60s)
- Orchestration: Step Functions state machine with:
  1. Kill-switch check (Parameter Store /dr/kill-switch)
  2. Verify-primary-down Lambda (3 retries, exponential backoff)
  3. Promote secondary (Aurora failover-global-cluster)
  4. Route 53 UPSERT to secondary ALB
  5. Verify-secondary-up Lambda
  6. Notify via SNS
  7. Human approval via SQS task token (no fixed Wait)
- Game-day drill: last run 2026-07-15, RTO measured 22min, RPO 1s
- Resilience Hub assessment score: 92
- Rollback path documented (reverse DNS, failback via snapshot rebuild)

Expected: AUTOMATED. The runbook covers the pilot-light strategy with
mapped RTO/RPO targets, a defined trigger (Route 53 health check), the
full failover sequence (verify -> promote -> DNS -> verify -> notify),
human approval via task token, and a documented rollback path.
