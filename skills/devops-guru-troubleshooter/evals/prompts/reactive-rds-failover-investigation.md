# Eval: reactive-rds-failover-investigation

**Difficulty:** hard
**Branch:** ROOT_CAUSE_FOUND — AWS-side AZ power event (not deployment) is the root cause; no rollback needed

## Prompt

Diagnose this DevOps Guru insight:
Insight ID: y-5678efgh in us-east-1
describe-insight: REACTIVE, HIGH, OPEN, Name="RDS Multi-AZ
failover detected for aurora-prod-cluster", StartTime=
2026-08-10T03:14Z.
list-anomalies-for-insight: CloudTrail event
FailoverDBCluster at 2026-08-10T03:14:22Z; Aurora
ConnectionAttempts dropped 90% during 03:14-03:18Z.
list-recommendations: DEPLOYMENT_FAILURE — "Investigate
recent deployments" (recommendation is heuristic; no
deployment occurred).
CloudTrail: No UpdateStack / deployment events in 03:00-03:20Z.
AWS Health Dashboard: AWS_AURORA_EVENT us-east-1a
"Power issue" at 2026-08-10T03:11Z through 03:45Z.
Region: us-east-1.
